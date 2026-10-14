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
from backend.services.schema_validator import validator as schema_validator
from backend.services.validation_service import validate_project
from engine.data.json_loader import load_project
from engine.data.json_writer import dump_project_document
from engine.project.project_migration import migrate_project


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
        self.assertEqual(imported["styles"], [])
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

    def test_v1_migration_preserves_project_content_and_serializes_as_current(self):
        legacy = deepcopy(self.example)
        legacy["version"] = 1
        migrated = migrate_project(legacy)

        self.assertEqual(legacy["version"], 1)
        self.assertNotIn("styles", legacy)
        self.assertEqual(migrated["version"], config.FORMAT_VERSION)
        self.assertEqual(migrated["styles"], [])
        self.assertEqual(migrated["drawings"], legacy["drawings"])
        self.assertEqual(
            migrated["scenes"][0]["layers"],
            legacy["scenes"][0]["layers"],
        )
        self.assertEqual(validate_project(migrated), [])

        serialized = json.loads(dump_project_document(legacy))
        self.assertEqual(serialized["version"], config.FORMAT_VERSION)
        self.assertEqual(serialized["drawings"], legacy["drawings"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.kae"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = load_project(path)
        self.assertEqual(loaded["version"], config.FORMAT_VERSION)
        self.assertEqual(loaded["drawings"], legacy["drawings"])

    def test_v1_project_api_load_and_save_migrates_to_current_version(self):
        legacy = deepcopy(self.example)
        legacy["id"] = "legacy_v1_project"
        legacy["version"] = 1

        with tempfile.TemporaryDirectory() as directory, patch.object(
            config, "PROJECTS_DIR", Path(directory)
        ):
            project_service.repo.save(legacy["id"], legacy)
            client = create_app().test_client()
            loaded_response = client.get(f"/api/projects/{legacy['id']}")
            self.assertEqual(loaded_response.status_code, 200)
            loaded = loaded_response.get_json()
            self.assertEqual(loaded["version"], config.FORMAT_VERSION)
            self.assertEqual(loaded["styles"], [])

            saved_response = client.put(
                f"/api/projects/{legacy['id']}", json=loaded
            )
            self.assertEqual(saved_response.status_code, 200)
            self.assertEqual(saved_response.get_json()["version"], config.FORMAT_VERSION)
            persisted = json.loads(
                (Path(directory) / legacy["id"] / "project.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(persisted["version"], config.FORMAT_VERSION)
            self.assertEqual(persisted["drawings"], legacy["drawings"])

    def test_project_schema_accepts_styles_cinematic_tracks_and_rig_constraints(self):
        project = deepcopy(self.example)
        project["version"] = config.FORMAT_VERSION
        project["styles"] = [
            {
                "id": "ink_style",
                "dash": {"array": [4, 2]},
                "gradient": {
                    "type": "linear",
                    "stops": [
                        {"offset": 0, "color": "#111111"},
                        {"offset": 1, "color": "#eeeeee"},
                    ],
                },
            }
        ]
        project["drawings"]["d_ground"]["strokes"][0]["style_id"] = "ink_style"
        project["scenes"][0]["camera"]["transform"].update(
            {"z": 24, "rotation_x": 5, "rotation_y": -8}
        )
        project["scenes"][0]["camera"]["tracks"] = {
            "scale_y": [{"t": 0, "v": 1}, {"t": 23, "v": 1.1}],
            "rotation_y": [{"t": 0, "v": 0}, {"t": 23, "v": 12}],
            "fov": [{"t": 0, "v": 60}, {"t": 23, "v": 45}],
        }
        project["characters"] = [
            {
                "id": "character_1",
                "name": "Rigged character",
                "parts": [{"id": "torso", "name": "Torso", "strokes": []}],
            }
        ]
        project["rigs"] = [
            {
                "id": "rig_1",
                "name": "Character rig",
                "character_id": "character_1",
                "bones": [
                    {
                        "id": "bone_1",
                        "name": "Torso",
                        "character_part_id": "torso",
                        "pivot": {"x": 0, "y": 0},
                    }
                ],
                "constraints": [
                    {
                        "type": "rotation_limit",
                        "bone_id": "bone_1",
                        "min": -45,
                        "max": 45,
                    }
                ],
            }
        ]

        self.assertEqual(schema_validator.validate_project(project), (True, None))
        self.assertEqual(validate_project(project), [])


if __name__ == "__main__":
    unittest.main()
