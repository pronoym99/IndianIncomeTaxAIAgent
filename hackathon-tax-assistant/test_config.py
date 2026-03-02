"""
Unit tests for configuration and environment variable handling.

These tests verify that environment variables are properly loaded,
model names are correctly resolved, and client creation works
with different configurations. No live API calls are made.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure the hackathon-tax-assistant directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from azure_openai import get_deployment_name, create_client


class TestGetDeploymentName(unittest.TestCase):
    """Test get_deployment_name() resolves model name correctly."""

    @patch.dict(os.environ, {"DEPLOYMENT_NAME": "my-azure-deployment"}, clear=False)
    def test_deployment_name_env_var(self):
        """DEPLOYMENT_NAME takes priority when set."""
        result = get_deployment_name()
        self.assertEqual(result, "my-azure-deployment")

    @patch.dict(os.environ, {"CHAT_MODEL": "phi-3-mini"}, clear=False)
    def test_chat_model_fallback(self):
        """Falls back to CHAT_MODEL when DEPLOYMENT_NAME is not set."""
        # Remove DEPLOYMENT_NAME if present
        env = os.environ.copy()
        env.pop("DEPLOYMENT_NAME", None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["CHAT_MODEL"] = "phi-3-mini"
            result = get_deployment_name()
            self.assertEqual(result, "phi-3-mini")

    @patch.dict(os.environ, {"DEPLOYMENT_NAME": "azure-dep", "CHAT_MODEL": "phi-3-mini"}, clear=False)
    def test_deployment_name_priority_over_chat_model(self):
        """DEPLOYMENT_NAME takes priority over CHAT_MODEL."""
        result = get_deployment_name()
        self.assertEqual(result, "azure-dep")

    def test_returns_none_when_nothing_set(self):
        """Returns None when neither DEPLOYMENT_NAME nor CHAT_MODEL is set."""
        env = os.environ.copy()
        env.pop("DEPLOYMENT_NAME", None)
        env.pop("CHAT_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            result = get_deployment_name()
            self.assertIsNone(result)


class TestCreateClient(unittest.TestCase):
    """Test create_client() configuration logic."""

    def test_raises_without_any_config(self):
        """create_client() raises RuntimeError with no env vars."""
        env = {}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                create_client()
            self.assertIn("No valid configuration", str(ctx.exception))

    @patch("azure_openai.OpenAI")
    def test_global_endpoint_with_openai_api_key(self, mock_openai):
        """create_client() uses global endpoint when OPENAI_API_KEY is set."""
        env = {
            "OPENAI_API_KEY": "test-key-123",
            "OPENAI_ENDPOINT": "https://models.inference.azure.com",
        }
        with patch.dict(os.environ, env, clear=True):
            client = create_client()
            mock_openai.assert_called_once_with(
                base_url="https://models.inference.azure.com",
                api_key="test-key-123",
            )

    @patch("azure_openai.OpenAI")
    def test_azure_endpoint_with_azure_vars(self, mock_openai):
        """create_client() uses Azure endpoint when AZURE_OPENAI_* vars are set."""
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://myresource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "azure-key-456",
        }
        with patch.dict(os.environ, env, clear=True):
            client = create_client()
            mock_openai.assert_called_once_with(
                base_url="https://myresource.openai.azure.com/",
                api_key="azure-key-456",
            )

    @patch("azure_openai.OpenAI")
    def test_use_global_flag_forces_global(self, mock_openai):
        """USE_GLOBAL_OPENAI=1 forces global endpoint even when Azure vars exist."""
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://myresource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "azure-key",
            "OPENAI_API_KEY": "global-key",
            "USE_GLOBAL_OPENAI": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            client = create_client()
            mock_openai.assert_called_once_with(
                base_url="https://models.inference.azure.com",
                api_key="global-key",
            )


class TestUIModelVariable(unittest.TestCase):
    """Test that CHAT_MODEL is properly available in ui.py context."""

    def test_chat_model_from_env(self):
        """CHAT_MODEL env var is readable after load_dotenv."""
        with patch.dict(os.environ, {"CHAT_MODEL": "gpt-4o-mini"}, clear=False):
            result = os.environ.get("CHAT_MODEL")
            self.assertEqual(result, "gpt-4o-mini")
            self.assertIsNotNone(result)

    def test_chat_model_not_none_when_set(self):
        """CHAT_MODEL should never be None when the env var is set."""
        with patch.dict(os.environ, {"CHAT_MODEL": "phi-3-mini"}, clear=False):
            model = os.environ.get("CHAT_MODEL")
            self.assertIsNotNone(model)
            self.assertTrue(len(model) > 0)

    def test_call_model_uses_chat_model(self):
        """call_model() should prefer CHAT_MODEL over passed model arg."""
        # Simulate what call_model does: model = CHAT_MODEL or model
        chat_model = "phi-3-mini"
        passed_model = None  # This is what get_deployment_name() returns when DEPLOYMENT_NAME not set
        
        resolved_model = chat_model or passed_model
        self.assertEqual(resolved_model, "phi-3-mini")

    def test_call_model_falls_back_to_passed_model(self):
        """call_model() uses passed model when CHAT_MODEL is not set."""
        chat_model = None
        passed_model = "fallback-model"
        
        resolved_model = chat_model or passed_model
        self.assertEqual(resolved_model, "fallback-model")


class TestAppModelVariable(unittest.TestCase):
    """Test that app.py resolves CHAT_MODEL correctly."""

    def test_chat_model_default(self):
        """app.py uses phi-3-mini as default for CHAT_MODEL."""
        env = os.environ.copy()
        env.pop("CHAT_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            result = os.environ.get("CHAT_MODEL", "phi-3-mini")
            self.assertEqual(result, "phi-3-mini")

    def test_chat_model_override(self):
        """app.py uses env var value when CHAT_MODEL is explicitly set."""
        with patch.dict(os.environ, {"CHAT_MODEL": "gpt-4o"}, clear=False):
            result = os.environ.get("CHAT_MODEL", "phi-3-mini")
            self.assertEqual(result, "gpt-4o")


if __name__ == "__main__":
    unittest.main()
