import json

from backend.app.application import create_app
from backend.services import mcp_connector_service as mcp


def test_initialize_negotiates_protocol_version():
    result = mcp.handle_rpc({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
    })
    assert result["result"]["protocolVersion"] == "2025-06-18"
    assert result["result"]["capabilities"]["tools"]["listChanged"] is False


def test_tools_are_advertised_with_schemas():
    result = mcp.handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {item["name"] for item in result["result"]["tools"]}
    assert {"kae_list_projects", "kae_get_project", "kae_get_scene_context", "kae_add_drawing", "kae_append_strokes", "kae_create_drawing_layer", "kae_update_layer", "kae_delete_layer"} <= names


def test_unknown_method_returns_json_rpc_error():
    result = mcp.handle_rpc({"jsonrpc": "2.0", "id": 3, "method": "made/up"})
    assert result["error"]["code"] == -32601


def test_notifications_do_not_return_response():
    assert mcp.handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_bearer_auth_requires_configured_key(monkeypatch):
    monkeypatch.delenv("KAE_MCP_API_KEY", raising=False)
    assert mcp.authenticate("Bearer secret") == (False, "KAE_MCP_API_KEY is not configured")
    monkeypatch.setenv("KAE_MCP_API_KEY", "right-secret")
    assert mcp.authenticate("Bearer wrong-secret") == (False, "Invalid or missing bearer token")
    assert mcp.authenticate("Bearer right-secret") == (True, "")


def test_http_endpoint_requires_auth(monkeypatch):
    monkeypatch.setenv("KAE_MCP_API_KEY", "right-secret")
    client = create_app().test_client()
    response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert response.status_code == 401
    response = client.post("/mcp", headers={"Authorization": "Bearer right-secret"}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert response.status_code == 200
    assert response.get_json()["result"]["protocolVersion"] == "2025-06-18"
