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
        for path in ("/", "/api/status", "/api/alarms", "/api/history", "/api/telegrams", "/api/dpts", "/api/ready", "/static/app.js"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.get("/health/live").status_code, 200)

    def test_web_and_security_headers(self):
        response = self.client.get("/", auth=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Störungen", response.text)
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
