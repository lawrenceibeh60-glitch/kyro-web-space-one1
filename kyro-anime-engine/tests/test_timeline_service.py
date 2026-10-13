import unittest
from copy import deepcopy
from unittest.mock import patch

from backend.app.exceptions import ApiError
from backend.services import timeline_service


class ApplyScriptTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            "scenes": [
                {
                    "id": "scene_1",
                    "layers": [{"id": "layer_1", "tracks": {}}],
                }
            ]
        }

    def test_invalid_operation_does_not_save_prior_changes(self):
        with patch.object(timeline_service.repo, "load", return_value=deepcopy(self.project)), \
                patch.object(timeline_service.repo, "save") as save, \
                patch.object(timeline_service, "validate_project", return_value=[]):
            with self.assertRaises(ApiError):
                timeline_service.apply_script(
                    "project_1",
                    {
                        "ops": [
                            {
                                "op": "set_key",
                                "scene_id": "scene_1",
                                "layer_id": "layer_1",
                                "channel": "x",
                                "time": 0,
                                "value": 7,
                            },
                            {"op": "unsupported"},
                        ]
                    },
                )

        save.assert_not_called()

    def test_valid_operations_save_once(self):
        with patch.object(timeline_service.repo, "load", return_value=deepcopy(self.project)), \
                patch.object(timeline_service.repo, "save") as save, \
                patch.object(timeline_service, "validate_project", return_value=[]):
            result = timeline_service.apply_script(
                "project_1",
                {
                    "ops": [
                        {
                            "op": "set_key",
                            "scene_id": "scene_1",
                            "layer_id": "layer_1",
                            "channel": "x",
                            "time": 0,
                            "value": 7,
                        },
                        {
                            "op": "set_key",
                            "scene_id": "scene_1",
                            "layer_id": "layer_1",
                            "channel": "x",
                            "time": 4,
                            "value": 12,
                        },
                    ]
                },
            )

        self.assertEqual(result["applied"], 2)
        self.assertEqual(result["results"], [
            {"t": 0, "v": 7, "ease": "linear"},
            {"t": 4, "v": 12, "ease": "linear"},
        ])
        save.assert_called_once()
        saved_project = save.call_args.args[1]
        self.assertEqual(
            saved_project["scenes"][0]["layers"][0]["tracks"]["x"],
            [
                {"t": 0, "v": 7, "ease": "linear"},
                {"t": 4, "v": 12, "ease": "linear"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
