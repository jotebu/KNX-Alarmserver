"""Authenticated API and German local dashboard. Single uvicorn worker only."""

import asyncio
import copy
import json
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exception_handlers import http_exception_handler

from . import __version__
from .knx import Monitor
from .config import validate_knx
from .ets import MAX_BYTES, parse_export

STATIC = Path(__file__).parent / "static"


def create_app(config, store, update_manager=None, version_checker=None):
    from .versions import VersionChecker
    versions = version_checker if version_checker is not None else VersionChecker()
    from .updates import DashboardUpdate
    updater = update_manager if update_manager is not None else DashboardUpdate()
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
    cookie_name = 'knx_session'

    def user(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
        token = request.cookies.get(cookie_name)
        account = store.session_user(token) if token else None
        if token is None and credentials is not None and store.authenticate(credentials.username, credentials.password):
            account = store.account(credentials.username)
        if account is None:
            # Browser uses the form; curl can still send Basic credentials explicitly.
            raise HTTPException(status_code=401, detail='Anmeldung erforderlich')
        request.state.account = account
        return account['username']

    def admin(request: Request, username=Depends(user)):
        if request.state.account['role'] != 'admin':
            raise HTTPException(status_code=403, detail='Nur fuer Admins erlaubt')
        return username

    def acknowledger(request: Request, username=Depends(user)):
        if request.state.account['role'] not in {'admin', 'user'}:
            raise HTTPException(status_code=403, detail='Viewer duerfen nicht quittieren')
        return username

    def identity(request, username):
        role = request.state.account['role']
        return {'user': username, 'role': role,
                'permissions': {'configure': role == 'admin', 'acknowledge': role in {'admin', 'user'}}}

    def action(request, expected):
        if (request.headers.get('X-Alarmserver-Action') != expected
                or request.headers.get('Sec-Fetch-Site') == 'cross-site'):
            raise HTTPException(status_code=403, detail='Aktionsheader fehlt oder fremde Herkunft')
        origin = request.headers.get('Origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(status_code=403, detail='Fremde Herkunft')

    async def json_body(request, max_bytes=8192):
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > max_bytes:
                raise HTTPException(status_code=413, detail='Anfrage zu gross')
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError()
            return payload
        except (ValueError, UnicodeError):
            raise HTTPException(status_code=422, detail='JSON-Objekt erwartet') from None

    @app.exception_handler(HTTPException)
    async def auth_page(request, error):
        if error.status_code == 401 and request.url.path in {'/', '/telegrams', '/knx', '/ets', '/users', '/versions', '/account/password'}:
            return FileResponse(STATIC / 'login.html', status_code=401)
        return await http_exception_handler(request, error)

    @app.get('/login')
    async def login_page():
        return FileResponse(STATIC / 'login.html')

    @app.post('/api/login')
    async def login(request: Request):
        action(request, 'login')
        payload = await json_body(request)
        if (set(payload) != {'username', 'password'}
                or not isinstance(payload['username'], str) or len(payload['username']) > 64
                or not isinstance(payload['password'], str) or len(payload['password']) > 1024):
            raise HTTPException(status_code=422, detail='Benutzername und Passwort erforderlich')
        token = await asyncio.to_thread(store.login, payload['username'], payload['password'])
        if token is None:
            raise HTTPException(status_code=401, detail='Benutzername oder Passwort falsch')
        await asyncio.to_thread(store.logout, request.cookies.get(cookie_name))
        response = JSONResponse({'ok': True})
        response.set_cookie(cookie_name, token, max_age=43200, httponly=True,
                            secure=request.url.scheme == 'https', samesite='strict', path='/')
        return response

    @app.post('/api/logout')
    def logout(request: Request):
        action(request, 'logout')
        store.logout(request.cookies.get(cookie_name))
        response = JSONResponse({'ok': True})
        response.delete_cookie(cookie_name, path='/')
        return response

    @app.post('/api/account/password')
    async def change_password(request: Request, username=Depends(user)):
        action(request, 'change-password')
        payload = await json_body(request)
        if (set(payload) != {'current_password', 'new_password'}
                or not isinstance(payload['current_password'], str)
                or len(payload['current_password']) > 1024):
            raise HTTPException(status_code=422, detail='Bisheriges und neues Passwort erforderlich')
        try:
            await asyncio.to_thread(store.change_own_password, username,
                                    payload['current_password'], payload['new_password'])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        response = JSONResponse({'ok': True})
        response.delete_cookie(cookie_name, path='/')
        return response

    @app.get('/api/version')
    async def version_check(refresh: bool = False, username=Depends(user)):
        return await asyncio.to_thread(versions.check, force=refresh)

    @app.get('/api/versions')
    async def version_history(refresh: bool = False, username=Depends(user)):
        return await asyncio.to_thread(versions.history, force=refresh)

    @app.get('/api/update')
    async def update_status(username=Depends(admin)):
        available_version = await asyncio.to_thread(versions.check)
        return {**updater.status(), **available_version}

    @app.post('/api/update')
    async def start_update(request: Request, username=Depends(admin)):
        action(request, 'update-server')
        async for chunk in request.stream():
            if chunk:
                raise HTTPException(status_code=422, detail='Update akzeptiert keine Parameter')
        available_version = await asyncio.to_thread(versions.check, force=True)
        if not available_version['check_ok'] or not available_version['update_available']:
            raise HTTPException(status_code=409, detail='Kein bestaetigtes neueres Update verfuegbar')
        try:
            result = await asyncio.to_thread(updater.start)
        except FileExistsError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from None
        except OSError:
            logging.getLogger(__name__).exception('Update konnte nicht angefordert werden')
            raise HTTPException(status_code=503, detail='Update-Dienst nicht verfuegbar') from None
        logging.getLogger(__name__).info('Dashboard-Update angefordert durch %s', username)
        return JSONResponse(result, status_code=202)

    @app.get('/api/users')
    def users(username=Depends(admin)):
        return store.users()

    @app.post('/api/users')
    async def create_user(request: Request, username=Depends(admin)):
        action(request, 'manage-users')
        payload = await json_body(request)
        if set(payload) != {'username', 'password', 'role'}:
            raise HTTPException(status_code=422, detail='Benutzername, Passwort und Rolle erforderlich')
        try:
            await asyncio.to_thread(store.create_user, payload['username'], payload['password'], payload['role'])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return {'ok': True}

    @app.put('/api/users/{target:path}')
    async def update_user(target: str, request: Request, username=Depends(admin)):
        action(request, 'manage-users')
        payload = await json_body(request)
        if 'role' not in payload or set(payload) - {'role', 'password'}:
            raise HTTPException(status_code=422, detail='Rolle und optional Passwort erforderlich')
        try:
            await asyncio.to_thread(store.update_user, target, payload['role'], payload.get('password'))
        except KeyError:
            raise HTTPException(status_code=404, detail='Benutzer nicht gefunden') from None
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return {'ok': True}

    @app.delete('/api/users/{target:path}')
    def delete_user(target: str, request: Request, username=Depends(admin)):
        action(request, 'manage-users')
        try:
            store.delete_user(target)
        except KeyError:
            raise HTTPException(status_code=404, detail='Benutzer nicht gefunden') from None
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return {'ok': True}

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

    @app.get("/api/status")
    def status(request: Request, username=Depends(user)):
        return {"version": __version__, **identity(request, username), "knx": monitor.status(), "started_at": store.started_at}

    @app.get("/api/dashboard")
    def dashboard(request: Request, view: str = "alarms", username=Depends(user)):
        if view not in {"alarms", "history", "telegrams"}:
            raise HTTPException(status_code=400, detail="Unbekannte Dashboard-Ansicht")
        result = {"status": {"version": __version__, **identity(request, username),
                             "knx": monitor.status(), "started_at": store.started_at},
                  "alarms": store.snapshot()}
        if view == "history":
            result["history"] = store.history()
        elif view == "telegrams":
            if request.state.account['role'] != 'admin':
                raise HTTPException(status_code=403, detail='Nur fuer Admins erlaubt')
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
    def telegrams(username=Depends(admin)):
        return list(monitor.telegrams)

    @app.get("/api/dpts")
    def dpts(username=Depends(user)):
        from .dpt import catalog
        return catalog()

    @app.get("/api/knx/config")
    def knx_config(username=Depends(admin)):
        return store.knx_settings(config["knx"])

    @app.get('/api/ets')
    def ets_catalog(username=Depends(admin)):
        return store.ets_catalog()

    async def read_ets(request):
        if (request.headers.get('X-Alarmserver-Action') != 'import-ets'
                or request.headers.get('Sec-Fetch-Site') == 'cross-site'):
            raise HTTPException(status_code=403, detail='Aktionsheader fehlt oder fremde Herkunft')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise HTTPException(status_code=413, detail='Maximal 4 MiB pro ETS-Datei')
        return bytes(raw)

    @app.post('/api/ets/preview')
    async def ets_preview(request: Request, filename: str, username=Depends(admin)):
        raw = await read_ets(request)
        try:
            result = await asyncio.to_thread(parse_export, raw, filename)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        current = await asyncio.to_thread(store.ets_catalog)
        existing = {e['address']: e for e in current['entries']}
        for entry in result['entries']:
            old = existing.get(entry['address'])
            entry['change'] = 'new' if old is None else 'unchanged' if old == entry else 'updated'
        result['revision'] = current['revision']
        result['existing_count'] = current['count']
        return result

    @app.post('/api/ets/import')
    async def ets_import(request: Request, filename: str, revision: str, digest: str,
                         mode: str = 'merge', username=Depends(admin)):
        raw = await read_ets(request)
        if mode not in {'merge', 'replace'}:
            raise HTTPException(status_code=422, detail='Importmodus ungueltig')
        try:
            parsed = await asyncio.to_thread(parse_export, raw, filename)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        if parsed['digest'] != digest:
            raise HTTPException(status_code=409, detail='Datei geaendert; Vorschau erneut laden')
        try:
            result = await asyncio.to_thread(store.import_ets, parsed['entries'], revision, mode)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        except Exception:
            logging.getLogger(__name__).exception('ETS-Import konnte nicht gespeichert werden')
            raise HTTPException(status_code=500, detail='Speichern fehlgeschlagen; bisherigen ETS-Katalog beibehalten') from None
        logging.getLogger(__name__).info('ETS-Import durch %s: %s', username, result)
        return result

    @app.put("/api/knx/config")
    async def save_knx_config(request: Request, username=Depends(admin)):
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
    def acknowledge(alarm_id: str, request: Request, username=Depends(acknowledger)):
        # A foreign HTML form cannot set this header. CORS is deliberately disabled.
        if request.headers.get("X-Alarmserver-Action") != "acknowledge":
            raise HTTPException(status_code=403, detail="Aktionsheader fehlt")
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise HTTPException(status_code=403, detail="Fremde Herkunft")
        try:
            return {"changed": store.acknowledge(alarm_id, username)}
        except KeyError:
            raise HTTPException(status_code=404, detail="Alarm nicht gefunden") from None

    @app.get('/telegrams')
    @app.get('/knx')
    @app.get('/ets')
    @app.get('/users')
    def admin_page(username=Depends(admin)):
        return FileResponse(STATIC / 'index.html')

    @app.get('/versions')
    @app.get('/account/password')
    def password_page(username=Depends(user)):
        return FileResponse(STATIC / 'index.html')

    @app.get("/")
    def index(username=Depends(user)):
        return FileResponse(STATIC / "index.html")

    @app.get('/static/login.js')
    async def login_script():
        return FileResponse(STATIC / 'login.js')

    @app.get('/static/style.css')
    async def stylesheet():
        return FileResponse(STATIC / 'style.css')

    @app.get("/static/{filename}")
    def static(filename: str, username=Depends(user)):
        if filename not in {"app.js", "style.css"}:
            raise HTTPException(status_code=404)
        return FileResponse(STATIC / filename)

    return app

