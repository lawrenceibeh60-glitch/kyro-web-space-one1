"""Tests for KAE AI's engine-aware capability context."""
import unittest

from backend.services.ai_capabilities import build_system_context, get_capabilities


class AICapabilitiesTests(unittest.TestCase):
    def test_inventory_describes_native_dimensions_and_real_routes(self):
        inventory = get_capabilities()
        self.assertEqual(inventory["format"]["name"], "kae")
        self.assertEqual(inventory["project_settings"]["width"]["max"], 8192)
        self.assertEqual(inventory["project_settings"]["fps"]["max"], 120)
        names = {tool["name"] for tool in inventory["tools"]}
        self.assertIn("timeline.keyframe", names)
        self.assertIn("drawings.create", names)
        self.assertIn("projects.save", names)

    def test_context_includes_real_scene_and_layer_ids(self):
        project = {
            "id": "sample",
            "name": "Sample",
            "version": 2,
            "settings": {"width": 1920, "height": 1080, "fps": 24, "duration_frames": 120},
            "scenes": [{
                "id": "scene_main",
                "name": "Main",
                "layers": [{"id": "layer_character", "name": "Character", "type": "drawing"}],
            }],
            "drawings": {"drawing_pose": {"id": "drawing_pose", "name": "Pose"}},
            "characters": [],
            "rigs": [],
        }
        context = build_system_context(project)
        self.assertIn("scene_main", context)
        self.assertIn("layer_character", context)
        self.assertIn("1920", context)
        self.assertIn("duration_frames", context)
        self.assertIn("Never invent a tool", context)


if __name__ == "__main__":
    unittest.main()
