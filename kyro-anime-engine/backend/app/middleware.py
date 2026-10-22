"""backend/app/middleware.py - hosted access gate and JSON error handling."""
import hmac
import logging
import os

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from backend.app.exceptions import ApiError

log = logging.getLogger("kae")


def _is_api():
    return request.path.startswith("/api/")


def install(app):
    @app.before_request
    def _hosted_access_gate():
        # Keep Render's health probe reachable. When configured, protect every
        # editor/API route with HTTP Basic Auth; the password is only an env var.
        if request.path in ("/health", "/api/health", "/mcp"):
            # /mcp has its own bearer-token authentication in mcp_connector.py.
            return None
        expected = os.environ.get("KAE_ACCESS_PASSWORD", "")
        if not expected:
            return None  # Local development remains frictionless.
        auth = request.authorization
        supplied = auth.password if auth and auth.type.lower() == "basic" else ""
        if not supplied or not hmac.compare_digest(supplied, expected):
            response = jsonify(error="Authentication required")
            response.status_code = 401
            response.headers["WWW-Authenticate"] = 'Basic realm="KYRO Animation Engine", charset="UTF-8"'
            return response
        return None

    @app.errorhandler(ApiError)
    def _api_error(e):
        return jsonify(error=e.message, details=e.details), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if _is_api():
            return jsonify(error=e.name, details=[e.description]), e.code
        return e

    @app.errorhandler(Exception)
    def _unhandled(e):
        log.exception("Unhandled error")
        return jsonify(error="Internal server error", details=[str(e)]), 500

    @app.after_request
    def _no_cache(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp
