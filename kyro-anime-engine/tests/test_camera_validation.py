import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from backend.services import project_service
from backend.services.validation_service import validate_project


class CameraValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        example = Path(__file__).parents[1] / "formats" / "examples" / "project.json"
        cls.project = json.loads(example.read_text(encoding="utf-8"))

    def test_existing_project_camera_is_valid(self):
        self.assertEqual(validate_project(deepcopy(self.project)), [])

    def test_zoom_is_limited_to_supported_range(self):
        project = deepcopy(self.project)
        project["scenes"][0]["camera"]["transform"]["scale_x"] = 0
        errors = validate_project(project)
        self.assertTrue(any("camera.transform.scale_x" in error for error in errors))

    def test_layer_depth_is_limited_to_supported_range(self):
        project = deepcopy(self.project)
        project["scenes"][0]["layers"][0]["depth"] = 2.1
        errors = validate_project(project)
        self.assertTrue(any(".depth:" in error for error in errors))

    def test_camera_only_accepts_pan_and_zoom_tracks(self):
        project = deepcopy(self.project)
        project["scenes"][0]["camera"]["tracks"] = {
            "opacity": [{"t": 0, "v": 0.5}]
        }
        errors = validate_project(project)
        self.assertTrue(any("unknown camera channel" in error for error in errors))

    def test_camera_roll_and_roll_tracks_are_validated(self):
        project = deepcopy(self.project)
        camera = project["scenes"][0]["camera"]
        camera["transform"]["rotation"] = 45
        camera["tracks"] = {"rotation": [{"t": 0, "v": 0}, {"t": 10, "v": -25}]}
        self.assertEqual(validate_project(project), [])
        camera["tracks"]["rotation"][1]["v"] = 4000
        errors = validate_project(project)
        self.assertTrue(any("camera.tracks.rotation[1].v" in error for error in errors))

    def test_new_projects_get_a_valid_camera_default(self):
        with patch.object(project_service.repo, "save"):
            project = project_service.create_project("Camera test")
        self.assertEqual(validate_project(project), [])
        self.assertEqual(project["scenes"][0]["camera"]["tracks"], {})

    def test_invalid_scene_light_is_reported(self):
        project = deepcopy(self.project)
        project["scenes"][0]["lights"] = [{
            "id": [], "x": 0, "y": 0, "radius": 12,
            "intensity": 1.5, "color": "warm",
        }]
        errors = validate_project(project)
        self.assertTrue(any("lights[0].id" in error for error in errors))
        self.assertTrue(any("lights[0].radius" in error for error in errors))
        self.assertTrue(any("lights[0].intensity" in error for error in errors))
        self.assertTrue(any("lights[0].color" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
