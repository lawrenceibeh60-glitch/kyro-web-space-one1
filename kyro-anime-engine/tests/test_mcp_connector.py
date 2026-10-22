import os
import unittest
from unittest.mock import patch

from backend.app.application import create_app
from backend.services import mcp_connector_service as mcp


class MCPConnectorTests(unittest.TestCase):
    def test_initialize_negotiates_protocol_version(self):
        result = mcp.handle_rpc({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        })
        self.assertEqual(result["result"]["protocolVersion"], "2025-06-18")
        self.assertFalse(result["result"]["capabilities"]["tools"]["listChanged"])

    def test_tools_are_advertised_with_schemas(self):
        result = mcp.handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {item["name"] for item in result["result"]["tools"]}
        self.assertTrue({"kae_list_projects", "kae_get_project", "kae_get_scene_context", "kae_add_drawing", "kae_append_strokes", "kae_create_drawing_layer", "kae_update_layer", "kae_delete_layer"} <= names)
        self.assertTrue(all(item["inputSchema"]["type"] == "object" for item in result["result"]["tools"]))

    def test_unknown_method_returns_json_rpc_error(self):
        result = mcp.handle_rpc({"jsonrpc": "2.0", "id": 3, "method": "made/up"})
        self.assertEqual(result["error"]["code"], -32601)

    def test_notifications_do_not_return_response(self):
        self.assertIsNone(mcp.handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_bearer_auth_requires_configured_key(self):
        with patch.dict(os.environ, {"KAE_MCP_API_KEY": ""}):
            self.assertEqual(mcp.authenticate("Bearer secret"), (False, "KAE_MCP_API_KEY is not configured"))
        with patch.dict(os.environ, {"KAE_MCP_API_KEY": "right-secret"}):
            self.assertEqual(mcp.authenticate("Bearer wrong-secret"), (False, "Invalid or missing bearer token"))
            self.assertEqual(mcp.authenticate("Bearer right-secret"), (True, ""))

    def test_http_endpoint_requires_auth(self):
        with patch.dict(os.environ, {"KAE_MCP_API_KEY": "right-secret", "KAE_ACCESS_PASSWORD": ""}):
            client = create_app().test_client()
            response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
            self.assertEqual(response.status_code, 401)
            response = client.post("/mcp", headers={"Authorization": "Bearer right-secret"}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["result"]["protocolVersion"], "2025-06-18")
            self.assertEqual(response.headers.get("MCP-Protocol-Version"), "2025-06-18")


if __name__ == "__main__":
    unittest.main()
