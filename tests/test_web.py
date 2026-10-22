import unittest

try:
    from fastapi.testclient import TestClient
    from knx_alarmserver.web import create_app
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from knx_alarmserver.store import Store
from test_core import ALARM


@unittest.skipUnless(AVAILABLE, "Web-Abhaengigkeiten nicht installiert")
class WebTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:", [ALARM])
        self.store.set_password("andy", "test-password-123")
        self.client = TestClient(create_app({"knx": {"enabled": False}}, self.store))
        self.client.__enter__()
        self.auth = ("andy", "test-password-123")

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.close()

    def test_all_building_data_requires_authentication(self):
        for path in ("/", "/api/dashboard", "/api/status", "/api/alarms", "/api/history", "/api/telegrams", "/api/dpts", "/api/ets", "/api/ready", "/static/app.js", "/static/date-range.js"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.get("/health/live").status_code, 200)

    def test_web_and_security_headers(self):
        response = self.client.get("/", auth=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Störungen", response.text)
        self.assertIn("/static/date-range.js", response.text)
        self.assertLess(response.text.index("/static/theme.js"),response.text.index("/static/style.css"))
        self.assertEqual(self.client.get("/static/theme.js").status_code,200)
        login=self.client.get("/login").text
        self.assertLess(login.index("/static/theme.js"),login.index("/static/style.css"))
        calendar = self.client.get("/static/date-range.js", auth=self.auth)
        self.assertEqual(calendar.status_code, 200)
        self.assertIn("window.AlarmDateRange", calendar.text)
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(self.client.get("/static/unknown", auth=self.auth).status_code, 404)

    def test_acknowledgement_uses_logged_in_identity_and_csrf_header(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        path = "/api/alarms/pump/acknowledge"
        self.assertEqual(self.client.post(path, auth=self.auth).status_code, 403)
        self.assertEqual(self.client.post(path, auth=self.auth, headers={"X-Alarmserver-Action": "acknowledge", "Sec-Fetch-Site": "cross-site"}).status_code, 403)
        response = self.client.post(path, auth=self.auth, headers={"X-Alarmserver-Action": "acknowledge"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.snapshot()[0]["acknowledged_by"], "andy")

    def test_disabled_knx_is_not_ready(self):
        self.assertEqual(self.client.get("/api/ready", auth=self.auth).status_code, 503)

    def test_missing_alarm(self):
        self.assertEqual(self.client.post("/api/alarms/missing/acknowledge", auth=self.auth,
                                         headers={"X-Alarmserver-Action": "acknowledge"}).status_code, 404)


    def test_dashboard_snapshot_authenticates_once_and_matches_selected_view(self):
        from unittest.mock import patch
        self.store.ingest("1/2/3", 1, "1.1.1")
        for view in ("alarms", "history", "telegrams"):
            with patch.object(self.store, "authenticate", wraps=self.store.authenticate) as auth:
                response = self.client.get("/api/dashboard", params={"view": view}, auth=self.auth)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(auth.call_count, 1)
            result = response.json()
            self.assertEqual(result["status"]["user"], "andy")
            self.assertEqual(result["alarms"][0]["status"], "active")
            if view != "alarms":
                self.assertIsInstance(result[view], list)
        self.assertEqual(self.client.get("/api/dashboard?view=invalid", auth=self.auth).status_code, 400)

    def test_liveness_remains_responsive_while_password_worker_is_busy(self):
        import asyncio
        import time
        import anyio
        import httpx
        from unittest.mock import patch

        async def scenario():
            limiter = anyio.to_thread.current_default_thread_limiter()
            previous_tokens = limiter.total_tokens
            limiter.total_tokens = 1
            started = asyncio.Event()
            loop = asyncio.get_running_loop()
            def slow_auth(username, password):
                loop.call_soon_threadsafe(started.set)
                time.sleep(0.3)
                return True
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.client.app),
                                             base_url='http://test', trust_env=False) as client:
                    with patch.object(self.store, 'authenticate', side_effect=slow_auth):
                        request = asyncio.create_task(client.get('/api/status', auth=self.auth))
                        try:
                            await asyncio.wait_for(started.wait(), 2)
                            response = await asyncio.wait_for(client.get('/health/live'), .2)
                            self.assertEqual(response.status_code, 200)
                            self.assertEqual((await request).status_code, 200)
                        finally:
                            await request
            finally:
                limiter.total_tokens = previous_tokens
        asyncio.run(scenario())


