"""Tests for durable-storage configuration detection."""
import os
import unittest
from unittest.mock import patch

from backend.storage import object_storage, postgres_projects


class DurableStorageConfigurationTests(unittest.TestCase):
    def test_postgres_is_not_configured_when_url_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(postgres_projects.configured())

    def test_postgres_is_configured_when_url_is_present(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://example"}, clear=True):
            self.assertTrue(postgres_projects.configured())

    def test_object_storage_requires_all_credentials(self):
        base = {
            "KAE_OBJECT_ENDPOINT_URL": "https://example.invalid",
            "KAE_OBJECT_BUCKET": "private-assets",
            "KAE_OBJECT_ACCESS_KEY_ID": "test-key",
        }
        with patch.dict(os.environ, base, clear=True):
            self.assertFalse(object_storage.configured())

    def test_object_storage_is_configured_with_all_required_values(self):
        env = {
            "KAE_OBJECT_ENDPOINT_URL": "https://example.invalid",
            "KAE_OBJECT_BUCKET": "private-assets",
            "KAE_OBJECT_ACCESS_KEY_ID": "test-key",
            "KAE_OBJECT_SECRET_ACCESS_KEY": "test-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(object_storage.configured())


if __name__ == "__main__":
    unittest.main()
