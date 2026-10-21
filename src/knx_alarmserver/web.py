"""Authenticated API and German local dashboard. Single uvicorn worker only."""

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import __version__
from .knx import Monitor

STATIC = Path(__file__).parent / "static"


def create_app(config, store):
    monitor = Monitor(config["knx"], store)

    async def housekeeping():
        while True:
            await asyncio.to_thread(store.prune)
            await asyncio.sleep(3600)

    @asynccontextmanager
    async def lifespan(app):
        if not store.has_users():
            raise RuntimeError("Zuerst mit knx-alarmserver user-add einen Benutzer anlegen")
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
    security = HTTPBasic(auto_error=False)

    def user(credentials: HTTPBasicCredentials | None = Depends(security)):
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
    def live():
        # No user or building information; used by installer and systemd checks.
        return {"status": "ok", "version": __version__}

    @app.get("/api/status")
    def status(username=Depends(user)):
        return {"version": __version__, "user": username, "knx": monitor.status(), "started_at": store.started_at}

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
