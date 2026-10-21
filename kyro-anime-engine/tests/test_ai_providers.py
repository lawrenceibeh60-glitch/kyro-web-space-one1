import os
import unittest
from unittest.mock import patch

from backend.app.application import create_app


class AIProviderHubTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"KAE_ACCESS_PASSWORD": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = create_app().test_client()

    def test_provider_catalog_includes_major_companies(self):
        response = self.client.get("/api/ai/providers")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.get_json()["providers"]}
        self.assertTrue({"openai", "anthropic", "groq", "openrouter", "xkiro", "custom"}.issubset(ids))

    def test_models_route_returns_models_without_echoing_key(self):
        with patch("backend.api.ai_providers.provider_request", return_value={"data": [{"id": "model-z"}, {"id": "model-a"}]}):
            response = self.client.post("/api/ai/providers/models", json={
                "provider_config": {"provider": "openai", "api_key": "secret-test-key", "model": "model-a"}
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["models"], ["model-a", "model-z"])
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))

    def test_connection_test_requires_a_key(self):
        response = self.client.post("/api/ai/providers/test", json={
            "provider_config": {"provider": "openai", "api_key": "", "model": "gpt-4.1-mini"}
        })
        self.assertEqual(response.status_code, 400)

    def test_connection_test_requires_a_real_text_response(self):
        with patch("backend.api.ai_providers.provider_request", return_value={
            "choices": [{"message": {"content": "KAE connection successful"}}], "model": "gpt-4.1-mini"
        }):
            response = self.client.post("/api/ai/providers/test", json={
                "provider_config": {"provider": "openai", "api_key": "secret-test-key", "model": "gpt-4.1-mini"}
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))

    def test_http_custom_provider_urls_are_rejected(self):
        response = self.client.post("/api/ai/providers/models", json={
            "provider_config": {"provider": "custom", "base_url": "http://example.com/v1", "api_key": "secret", "model": "test"}
        })
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
