"""KAE request middleware: API errors, optional HTTP Basic auth, and no-cache."""
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
    def _require_access_password():
        expected = os.environ.get("KAE_ACCESS_PASSWORD", "").strip()
        # Local development remains frictionless; hosted deployments should set this.
        if not expected or request.path == "/api/health":
            return None

        auth = request.authorization
        supplied = auth.password if auth and auth.type.lower() == "basic" else ""
        username = auth.username if auth and auth.type.lower() == "basic" else ""
        if username == "kae" and hmac.compare_digest(supplied or "", expected):
            return None

        response = jsonify(error="Authentication required", details=["Sign in to access KYRO Animation Engine."])
        response.status_code = 401
        response.headers["WWW-Authenticate"] = 'Basic realm="KYRO Animation Engine", charset="UTF-8"'
        return response

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
