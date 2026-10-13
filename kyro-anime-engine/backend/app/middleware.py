"""backend/app/middleware.py - JSON error handling + no-cache for dev."""
import logging

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from backend.app.exceptions import ApiError

log = logging.getLogger("kae")


def _is_api():
    return request.path.startswith("/api/")


def install(app):
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
