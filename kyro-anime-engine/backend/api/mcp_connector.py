"""Authenticated MCP Streamable HTTP endpoint for external AI clients."""
from flask import Blueprint, jsonify, request, make_response

from backend.services import mcp_connector_service as mcp

bp = Blueprint("mcp_connector", __name__)


@bp.route("/mcp", methods=["POST"])
def mcp_endpoint():
    ok, reason = mcp.authenticate(request.headers.get("Authorization", ""))
    if not ok:
        status = 503 if reason == "KAE_MCP_API_KEY is not configured" else 401
        response = jsonify(error=reason)
        response.status_code = status
        if status == 401:
            response.headers["WWW-Authenticate"] = 'Bearer realm="KAE MCP", error="invalid_token"'
        return response

    message = request.get_json(silent=True)
    if isinstance(message, list):
        responses = [mcp.handle_rpc(item) for item in message]
        responses = [item for item in responses if item is not None]
        return jsonify(responses) if responses else ("", 202)

    response_data = mcp.handle_rpc(message)
    if response_data is None:
        return "", 202
    response = make_response(jsonify(response_data))
    response.headers["MCP-Protocol-Version"] = request.headers.get("MCP-Protocol-Version", "2025-11-25")
    return response


@bp.route("/mcp", methods=["GET", "DELETE", "PUT", "PATCH"])
def mcp_unsupported_method():
    response = jsonify(error="This KAE MCP endpoint accepts JSON-RPC POST requests only.")
    response.status_code = 405
    response.headers["Allow"] = "POST"
    return response
