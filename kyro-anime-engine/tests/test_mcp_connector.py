import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import config
from backend.services import project_service
from backend.storage import project_repository as repo

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
        self.assertTrue({"kae_list_projects", "kae_create_project", "kae_get_project", "kae_get_scene_context", "kae_add_drawing", "kae_append_strokes", "kae_create_drawing_layer", "kae_update_layer", "kae_delete_layer"} <= names)
        self.assertTrue(all(item["inputSchema"]["type"] == "object" for item in result["result"]["tools"]))

    def test_unknown_method_returns_json_rpc_error(self):
        result = mcp.handle_rpc({"jsonrpc": "2.0", "id": 3, "method": "made/up"})
        self.assertEqual(result["error"]["code"], -32601)

    def test_non_object_params_returns_invalid_params(self):
        result = mcp.handle_rpc({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": ["not", "named"]
        })
        self.assertEqual(result["error"]["code"], -32602)
        self.assertIn("params must be an object", result["error"]["message"])

    def test_invalid_notification_params_do_not_return_response(self):
        result = mcp.handle_rpc({
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": []
        })
        self.assertIsNone(result)

    def test_notifications_do_not_return_response(self):
        self.assertIsNone(mcp.handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_bearer_auth_requires_configured_key(self):
        with patch.dict(os.environ, {"KAE_MCP_API_KEY": ""}):
            self.assertEqual(mcp.authenticate("Bearer secret"), (False, "KAE_MCP_API_KEY is not configured"))
        with patch.dict(os.environ, {"KAE_MCP_API_KEY": "right-secret"}):
            self.assertEqual(mcp.authenticate("Bearer wrong-secret"), (False, "Invalid or missing bearer token"))
            self.assertEqual(mcp.authenticate("Bearer right-secret"), (True, ""))


    def test_mcp_can_create_a_native_project(self):
        with TemporaryDirectory() as folder, patch.object(config, "PROJECTS_DIR", Path(folder)):
            result = mcp.call_tool("kae_create_project", {
                "name": "MCP-created project",
                "settings": {"width": 1920, "height": 1080, "fps": 24, "duration_frames": 48},
            })
            self.assertTrue(result["ok"])
            self.assertEqual(result["name"], "MCP-created project")
            saved = repo.load(result["project_id"])
            self.assertEqual(saved["settings"]["width"], 1920)
            self.assertEqual(saved["settings"]["height"], 1080)
            self.assertEqual(saved["scenes"][0]["id"], "scene_1")

    def test_create_project_rejects_invalid_settings_object(self):
        with self.assertRaisesRegex(Exception, "settings must be an object"):
            mcp.call_tool("kae_create_project", {"name": "Bad project", "settings": []})

    def test_drawing_can_be_added_and_placed_on_timeline(self):
        with TemporaryDirectory() as folder, patch.object(config, "PROJECTS_DIR", Path(folder)):
            project = project_service.create_project("MCP connector test")
            pid = project["id"]
            stroke = {
                "id": "mcp_stroke_1",
                "tool": "brush",
                "color": "#111111",
                "width": 3,
                "points": [[10, 10, 1], [30, 30, 1]],
            }
            created = mcp.call_tool("kae_add_drawing", {
                "project_id": pid, "drawing_id": "mcp_drawing_1",
                "name": "MCP test stroke", "strokes": [stroke],
            })
            self.assertTrue(created["ok"])
            placed = mcp.call_tool("kae_create_drawing_layer", {
                "project_id": pid, "scene_id": "scene_1",
                "layer_id": "mcp_layer_1", "name": "AI artwork",
                "drawing_id": "mcp_drawing_1", "start_frame": 0, "length": 24,
            })
            self.assertTrue(placed["ok"])
            saved = repo.load(pid)
            self.assertEqual(len(saved["drawings"]["mcp_drawing_1"]["strokes"]), 1)
            self.assertEqual(saved["scenes"][0]["layers"][-1]["id"], "mcp_layer_1")
            self.assertEqual(saved["scenes"][0]["layers"][-1]["exposures"][0]["drawing"], "mcp_drawing_1")

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
