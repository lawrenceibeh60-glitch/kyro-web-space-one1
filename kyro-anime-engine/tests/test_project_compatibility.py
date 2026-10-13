import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import config
from backend.app.application import create_app
from backend.app.exceptions import ApiError
from backend.services import project_service
from backend.services.validation_service import validate_project


class ProjectCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        example = Path(__file__).parents[1] / "formats" / "examples" / "project.json"
        cls.example = json.loads(example.read_text(encoding="utf-8"))

    def test_legacy_import_supplies_safe_project_defaults(self):
        legacy = {
            "name": "Legacy project",
            "settings": {"width": 640},
        }
        with patch.object(project_service.repo, "save") as save:
            imported = project_service.import_project(legacy)

        self.assertEqual(legacy, {"name": "Legacy project", "settings": {"width": 640}})
        self.assertEqual(imported["format"], "kae")
        self.assertEqual(imported["version"], config.FORMAT_VERSION)
        self.assertTrue(imported["id"])
        self.assertEqual(imported["settings"]["width"], 640)
        self.assertEqual(imported["settings"]["height"], 720)
        self.assertEqual(imported["scenes"][0]["layers"][0]["exposures"], [])
        for field in ("palette", "characters", "effects", "rigs", "audio"):
            self.assertEqual(imported[field], [])
        self.assertEqual(validate_project(imported), [])
        save.assert_called_once_with(imported["id"], imported)

    def test_future_project_version_is_rejected_without_writing(self):
        project = deepcopy(self.example)
        project["version"] = config.FORMAT_VERSION + 1
        with patch.object(project_service.repo, "save") as save:
            with self.assertRaises(ApiError) as raised:
                project_service.import_project(project)
            with self.assertRaises(ApiError):
                project_service.save_project(project["id"], project)

        self.assertEqual(raised.exception.status, 422)
        self.assertIn("newer than the supported version", raised.exception.message)
        save.assert_not_called()

    def test_large_project_import_and_reload_round_trip(self):
        project = deepcopy(self.example)
        project["id"] = "large_compatibility_fixture"
        project["name"] = "Large compatibility fixture"
        drawing_id = "bulk_drawing"
        project["drawings"][drawing_id] = {
            "id": drawing_id,
            "name": "Bulk drawing",
            "strokes": [
                {
                    "id": f"bulk_stroke_{stroke_index}",
                    "points": [
                        [point_index, stroke_index, 1]
                        for point_index in range(100)
                    ],
                }
                for stroke_index in range(32)
            ],
        }
        template = project["scenes"][0]["layers"][0]
        project["scenes"][0]["layers"] = [
            {
                **deepcopy(template),
                "id": f"bulk_layer_{layer_index}",
                "name": f"Bulk layer {layer_index}",
                "exposures": [{"start": 0, "length": 24, "drawing": drawing_id}],
            }
            for layer_index in range(128)
        ]
        self.assertEqual(validate_project(project), [])

        with tempfile.TemporaryDirectory() as directory, patch.object(
            config, "PROJECTS_DIR", Path(directory)
        ):
            client = create_app().test_client()
            response = client.post("/api/projects/import", json=project)
            self.assertEqual(response.status_code, 201)
            imported = response.get_json()

            loaded_response = client.get(f"/api/projects/{imported['id']}")
            self.assertEqual(loaded_response.status_code, 200)
            self.assertEqual(loaded_response.get_json(), imported)

        self.assertEqual(len(imported["scenes"][0]["layers"]), 128)
        self.assertEqual(len(imported["drawings"][drawing_id]["strokes"]), 32)


if __name__ == "__main__":
    unittest.main()
