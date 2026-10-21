"""Authenticated API and German local dashboard. Single uvicorn worker only."""

import asyncio
import copy
import json
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import __version__
from .knx import Monitor
from .config import validate_knx

STATIC = Path(__file__).parent / "static"


def create_app(config, store):
    auth_enabled = os.environ.get("KNX_ALARMSERVER_DISABLE_AUTH") != "1"
    initial = store.knx_settings(config["knx"])["config"]
    validate_knx(initial)
    monitor = Monitor(initial, store)
    settings_lock = asyncio.Lock()

    async def housekeeping():
        while True:
            await asyncio.to_thread(store.prune)
            await asyncio.sleep(3600)

    @asynccontextmanager
    async def lifespan(app):
        if auth_enabled and not store.has_users():
            raise RuntimeError("Zuerst mit knx-alarmserver user-add einen Benutzer anlegen")
        if not auth_enabled:
            logging.getLogger(__name__).warning("Testmodus: Web-Anmeldung deaktiviert; Zugriff ohne Benutzerkonto")
        await monitor.start()
        task = asyncio.create_task(housekeeping())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await monitor.stop()

    app = FastAPI(title="KNX Alarmserver", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.monitor = monitor
    # In test mode do not parse even cached or malformed Basic credentials.
    security = HTTPBasic(auto_error=False) if auth_enabled else lambda: None

    def user(credentials: HTTPBasicCredentials | None = Depends(security)):
        if not auth_enabled:
            return "ohne-anmeldung"
        if credentials is None or not store.authenticate(credentials.username, credentials.password):
            raise HTTPException(status_code=401, detail="Anmeldung erforderlich",
                                headers={"WWW-Authenticate": 'Basic realm="KNX Alarmserver", charset="UTF-8"'})
        return credentials.username

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.get("/health/live")
    async def live():
        # No user or building information; used by installer and systemd checks.
        return {"status": "ok", "version": __version__}

    if not auth_enabled:
        @app.get("/test/hallo", response_class=HTMLResponse)
        async def hello():
            return '<!doctype html><html lang="de"><meta charset="utf-8"><title>Hallo Welt</title><body>Hallo Welt</body></html>'

    @app.get("/api/status")
    def status(username=Depends(user)):
        return {"version": __version__, "user": username, "knx": monitor.status(), "started_at": store.started_at}

    @app.get("/api/dashboard")
    def dashboard(view: str = "alarms", username=Depends(user)):
        if view not in {"alarms", "history", "telegrams"}:
            raise HTTPException(status_code=400, detail="Unbekannte Dashboard-Ansicht")
        result = {"status": {"version": __version__, "user": username,
                             "knx": monitor.status(), "started_at": store.started_at},
                  "alarms": store.snapshot()}
        if view == "history":
            result["history"] = store.history()
        elif view == "telegrams":
            result["telegrams"] = list(monitor.telegrams)
        return result

    @app.get("/api/ready")
    def ready(username=Depends(user)):
        state = monitor.status()
        return JSONResponse(state, status_code=200 if state["ready"] else 503)

    @app.get("/api/alarms")
    def alarms(username=Depends(user)):
        return store.snapshot()

    @app.get("/api/history")
    def history(username=Depends(user)):
        return store.history()

    @app.get("/api/telegrams")
    def telegrams(username=Depends(user)):
        return list(monitor.telegrams)

    @app.get("/api/dpts")
    def dpts(username=Depends(user)):
        from .dpt import catalog
        return catalog()

    @app.get("/api/knx/config")
    def knx_config(username=Depends(user)):
        return store.knx_settings(config["knx"])

    @app.put("/api/knx/config")
    async def save_knx_config(request: Request, username=Depends(user)):
        nonlocal monitor
        if request.headers.get("X-Alarmserver-Action") != "configure-knx" or request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise HTTPException(status_code=403, detail="Aktionsheader fehlt oder fremde Herkunft")
        try:
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 65536:
                    raise HTTPException(status_code=413, detail="Konfiguration zu gross")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or set(payload) != {"config", "revision"}:
                raise ValueError("config und revision erforderlich")
            proposed = copy.deepcopy(payload["config"])
            validate_knx(proposed)
        except (ValueError, TypeError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        async with settings_lock:
            current = store.knx_settings(config["knx"])
            if payload["revision"] != current["revision"]:
                raise HTTPException(status_code=409, detail="Konfiguration inzwischen geaendert. Neu laden und erneut bearbeiten.")
            previous = monitor
            replacement = Monitor(proposed, store)
            await previous.stop()
            try:
                await replacement.start()
                store.save_knx_settings(proposed)
            except Exception:
                await replacement.stop()
                await previous.start()
                logging.getLogger(__name__).exception("KNX-Konfiguration konnte nicht uebernommen werden")
                raise HTTPException(status_code=500, detail="Speichern fehlgeschlagen; bisherige Konfiguration wieder aktiviert") from None
            monitor = replacement
            app.state.monitor = monitor
            logging.getLogger(__name__).info("KNX-Konfiguration durch %s aktualisiert", username)
            return store.knx_settings(config["knx"])

    @app.post("/api/alarms/{alarm_id}/acknowledge")
    def acknowledge(alarm_id: str, request: Request, username=Depends(user)):
        # A foreign HTML form cannot set this header. CORS is deliberately disabled.
        if request.headers.get("X-Alarmserver-Action") != "acknowledge":
            raise HTTPException(status_code=403, detail="Aktionsheader fehlt")
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise HTTPException(status_code=403, detail="Fremde Herkunft")
        try:
            return {"changed": store.acknowledge(alarm_id, username)}
        except KeyError:
            raise HTTPException(status_code=404, detail="Alarm nicht gefunden") from None

    @app.get("/")
    def index(username=Depends(user)):
        return FileResponse(STATIC / "index.html")

    @app.get("/static/{filename}")
    def static(filename: str, username=Depends(user)):
        if filename not in {"app.js", "style.css"}:
            raise HTTPException(status_code=404)
        return FileResponse(STATIC / filename)

    return app

