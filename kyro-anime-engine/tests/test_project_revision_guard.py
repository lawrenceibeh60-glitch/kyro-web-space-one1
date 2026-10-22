import unittest
from unittest.mock import patch

from backend.app.application import create_app


class ProjectRevisionGuardTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.current = {
            "id": "revision-test",
            "name": "Revision Test",
            "modified": "2026-10-22T12:00:00Z",
        }

    def test_stale_save_returns_conflict_without_writing(self):
        with patch("backend.api.projects.svc.get_project", return_value=self.current), \
             patch("backend.api.projects.svc.save_project") as save:
            response = self.client.put(
                "/api/projects/revision-test",
                json={"_expected_modified": "2026-10-22T11:00:00Z", "name": "stale"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["details"]["current_modified"], self.current["modified"])
        save.assert_not_called()

    def test_matching_revision_is_saved_and_returns_revision_etag(self):
        updated = {**self.current, "name": "updated", "modified": "2026-10-22T12:05:00Z"}
        with patch("backend.api.projects.svc.get_project", return_value=self.current), \
             patch("backend.api.projects.svc.save_project", return_value=updated) as save:
            response = self.client.put(
                "/api/projects/revision-test",
                json={"_expected_modified": self.current["modified"], "name": "updated"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "updated")
        self.assertEqual(response.headers.get("ETag"), '"2026-10-22T12:05:00Z"')
        save.assert_called_once_with("revision-test", {"name": "updated"})


if __name__ == "__main__":
    unittest.main()
