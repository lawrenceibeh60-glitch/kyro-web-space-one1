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
