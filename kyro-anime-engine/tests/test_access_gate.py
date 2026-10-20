"""Hosted access-gate regression tests."""
import base64
import os
import unittest
from unittest.mock import patch

from flask import Flask

from backend.app import middleware


class AccessGateTests(unittest.TestCase):
    def make_app(self):
        app = Flask(__name__)
        middleware.install(app)

        @app.get("/protected")
        def protected():
            return {"status": "ok"}

        @app.get("/api/health")
        def health():
            return {"status": "ok"}

        return app

    @patch.dict(os.environ, {"KAE_ACCESS_PASSWORD": "test-secret"})
    def test_protected_route_requires_authentication(self):
        response = self.make_app().test_client().get("/protected")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response.headers.get("WWW-Authenticate", ""))

    @patch.dict(os.environ, {"KAE_ACCESS_PASSWORD": "test-secret"})
    def test_valid_basic_auth_can_access_route(self):
        token = base64.b64encode(b"kae:test-secret").decode("ascii")
        response = self.make_app().test_client().get(
            "/protected", headers={"Authorization": f"Basic {token}"}
        )
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"KAE_ACCESS_PASSWORD": "test-secret"})
    def test_health_route_remains_available_for_render(self):
        response = self.make_app().test_client().get("/api/health")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
