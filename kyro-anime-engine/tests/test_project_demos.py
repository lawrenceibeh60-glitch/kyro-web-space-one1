import unittest
from unittest.mock import patch

from backend.app.exceptions import ApiError
from backend.app.application import create_app
from backend.services import project_service
from backend.services.validation_service import validate_project


class ProjectDemoTests(unittest.TestCase):
    def test_each_demo_template_creates_a_valid_editable_project(self):
        with patch.object(project_service.repo, "save"):
            for template in project_service.DEMO_TEMPLATES:
                with self.subTest(template=template):
                    project = project_service.create_demo(template)
                    self.assertEqual(validate_project(project), [])
                    self.assertTrue(project["scenes"][0]["layers"])

    def test_parallax_demo_has_several_depth_planes_and_camera_motion(self):
        with patch.object(project_service.repo, "save"):
            project = project_service.create_demo("parallax")

        layers = project["scenes"][0]["layers"]
        self.assertGreaterEqual(len({layer["depth"] for layer in layers}), 3)
        self.assertTrue(project["scenes"][0]["camera"]["tracks"]["x"])

    def test_cinematic_demo_has_full_length_camera_choreography_and_front_profile_art(self):
        with patch.object(project_service.repo, "save"):
            try:
                project = project_service.create_demo("cinematic")
            except ApiError as error:
                self.fail(f"cinematic validation errors: {error.details!r}")

        self.assertEqual(project["settings"]["duration_frames"], 200)
        scene = project["scenes"][0]
        camera_tracks = scene["camera"]["tracks"]
        for channel in ("x", "y", "rotation", "scale_x", "scale_y"):
            with self.subTest(channel=channel):
                keys = camera_tracks[channel]
                self.assertEqual(keys[0]["t"], 0)
                self.assertEqual(keys[-1]["t"], 199)
                self.assertGreaterEqual(len(keys), 6)
        walker_layers = [
            layer for layer in scene["layers"]
            if layer.get("character_id") == "character_walker"
        ]
        self.assertEqual(len(walker_layers), 8)
        for layer in walker_layers:
            with self.subTest(layer=layer["id"]):
                self.assertEqual(
                    [(exposure["start"], exposure["length"])
                     for exposure in layer["exposures"]],
                    [(0, 100), (100, 100)],
                )
                self.assertEqual(layer["character_id"], "character_walker")
                self.assertTrue(layer.get("character_part_id"))
        rig = next(item for item in project["rigs"] if item["character_id"] == "character_walker")
        self.assertEqual(rig["animation"]["type"], "walk")
        self.assertTrue(rig["animation"]["enabled"])
        self.assertEqual(len(rig["bones"]), 8)
        self.assertNotIn("d_character_front", project["drawings"])
        self.assertNotIn("d_character_profile", project["drawings"])
        self.assertEqual(validate_project(project), [])

    def test_unknown_demo_template_is_rejected(self):
        with self.assertRaises(ApiError):
            project_service.create_demo("not-a-demo")

    def test_demo_template_route_returns_an_editable_project(self):
        app = create_app()
        with patch.object(project_service.repo, "save"):
            response = app.test_client().post("/api/projects/demo/parallax")

        self.assertEqual(response.status_code, 201)
        project = response.get_json()
        self.assertEqual(project["name"], "Parallax Ridge")
        self.assertEqual(validate_project(project), [])

    def test_demo_routes_support_get_and_post_for_all_templates(self):
        app = create_app()
        with patch.object(project_service.repo, "save"):
            client = app.test_client()
            for method in ("get", "post"):
                for template in [*project_service.DEMO_TEMPLATES, "bounce"]:
                    with self.subTest(method=method, template=template):
                        response = getattr(client, method)(f"/api/projects/demo/{template}")
                        self.assertEqual(response.status_code, 201)
                        self.assertEqual(validate_project(response.get_json()), [])

    def test_parallax_demo_includes_a_valid_scene_light(self):
        with patch.object(project_service.repo, "save"):
            project = project_service.create_demo("parallax")
        self.assertTrue(project["scenes"][0]["lights"])
        self.assertEqual(validate_project(project), [])


if __name__ == "__main__":
    unittest.main()
