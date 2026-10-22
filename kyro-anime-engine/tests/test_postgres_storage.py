"""Tests for KAE's PostgreSQL storage selection and URL handling."""
import os
import unittest
from unittest.mock import patch

from backend.app.exceptions import ApiError
from backend.storage import postgres_projects
from backend.storage import project_repository as repo


class PostgreSQLConfigurationTests(unittest.TestCase):
    def test_database_url_controls_storage_backend(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@db.example/kae"}):
            self.assertTrue(postgres_projects.configured())
            self.assertEqual(repo.backend_name(), "postgresql")
        with patch.dict(os.environ, {"DATABASE_URL": "   "}):
            self.assertFalse(postgres_projects.configured())
            self.assertEqual(repo.backend_name(), "filesystem")

    def test_legacy_postgres_scheme_is_normalized(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@db.example/kae"}):
            self.assertEqual(postgres_projects._url(), "postgresql://user:pass@db.example/kae")

    def test_empty_database_url_fails_clearly(self):
        with patch.dict(os.environ, {"DATABASE_URL": "  "}):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL is not configured"):
                postgres_projects._url()

    def test_repository_routes_project_reads_and_writes_to_postgres(self):
        document = {"id": "project_1", "name": "Test"}
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@db.example/kae"}):
            with patch.object(postgres_projects, "exists", return_value=True) as exists, \
                 patch.object(postgres_projects, "list_ids", return_value=["project_1"]) as list_ids, \
                 patch.object(postgres_projects, "load", return_value=document) as load, \
                 patch.object(postgres_projects, "save") as save, \
                 patch.object(postgres_projects, "delete", return_value=True) as delete:
                self.assertTrue(repo.exists("project_1"))
                self.assertEqual(repo.list_ids(), ["project_1"])
                self.assertEqual(repo.load("project_1"), document)
                repo.save("project_1", document)
                self.assertIsNone(repo.delete("project_1"))
                exists.assert_called_once_with("project_1")
                list_ids.assert_called_once_with()
                load.assert_called_once_with("project_1")
                save.assert_called_once_with("project_1", document)
                delete.assert_called_once_with("project_1")

    def test_invalid_project_ids_are_rejected_before_database_access(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@db.example/kae"}):
            with patch.object(postgres_projects, "load") as load:
                with self.assertRaises(ApiError):
                    repo.load("../unsafe")
                load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
