import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model_manager import ModelManager

class TestModelManager(unittest.TestCase):
    
    @patch('model_manager.OpenRouterProvider')
    @patch('model_manager.OllamaProvider')
    def test_startup_checks_auto_openrouter_valid(self, mock_ollama_cls, mock_openrouter_cls):
        # Setup mocks
        mock_or = mock_openrouter_cls.return_value
        mock_or.validate.return_value = (True, "Ready")
        mock_or.model = "deepseek/deepseek-chat"
        
        mock_ol = mock_ollama_cls.return_value
        mock_ol.validate.return_value = (True, "Ready")
        mock_ol.model = "llama3"
        
        # Test default/auto mode with valid OpenRouter
        with patch.dict(os.environ, {"MODEL_PROVIDER": "auto"}):
            mm = ModelManager()
            self.assertEqual(mm.active_provider, mock_or)

    @patch('model_manager.OpenRouterProvider')
    @patch('model_manager.OllamaProvider')
    def test_startup_checks_auto_openrouter_invalid(self, mock_ollama_cls, mock_openrouter_cls):
        # Setup mocks
        mock_or = mock_openrouter_cls.return_value
        mock_or.validate.return_value = (False, "Key missing")
        mock_or.model = "deepseek/deepseek-chat"
        
        mock_ol = mock_ollama_cls.return_value
        mock_ol.validate.return_value = (True, "Ready")
        mock_ol.model = "llama3"
        
        # Test auto mode with invalid OpenRouter but valid Ollama
        with patch.dict(os.environ, {"MODEL_PROVIDER": "auto"}):
            mm = ModelManager()
            self.assertEqual(mm.active_provider, mock_ol)

    @patch('model_manager.OpenRouterProvider')
    @patch('model_manager.OllamaProvider')
    def test_generate_fallback_to_ollama(self, mock_ollama_cls, mock_openrouter_cls):
        # Setup mocks
        mock_or = mock_openrouter_cls.return_value
        mock_or.validate.return_value = (True, "Ready")
        mock_or.model = "deepseek/deepseek-chat"
        mock_or.generate.side_effect = Exception("OpenRouter API error")
        
        mock_ol = mock_ollama_cls.return_value
        mock_ol.validate.return_value = (True, "Ready")
        mock_ol.model = "llama3"
        mock_ol.generate.return_value = ("Ollama response", [])
        
        with patch.dict(os.environ, {"MODEL_PROVIDER": "auto"}):
            mm = ModelManager()
            # Since auto is selected and or_valid is True, it starts with OpenRouter.
            # But OpenRouter generation fails, so it should fall back to Ollama.
            res_text, tools = mm.generate(system_prompt="sys", user_prompt="user")
            self.assertEqual(res_text, "Ollama response")
            mock_ol.generate.assert_called_once_with("sys", "user", None, None)

    @patch('model_manager.OpenRouterProvider')
    @patch('model_manager.OllamaProvider')
    def test_generate_forced_mode(self, mock_ollama_cls, mock_openrouter_cls):
        mock_or = mock_openrouter_cls.return_value
        mock_or.validate.return_value = (True, "Ready")
        mock_or.generate.return_value = ("OR response", [])
        
        mock_ol = mock_ollama_cls.return_value
        mock_ol.validate.return_value = (True, "Ready")
        mock_ol.generate.return_value = ("Ollama response", [])
        
        # Force openrouter
        with patch.dict(os.environ, {"MODEL_PROVIDER": "openrouter"}):
            mm = ModelManager()
            res_text, _ = mm.generate("sys", "user")
            self.assertEqual(res_text, "OR response")
            mock_or.generate.assert_called_once()
            mock_ol.generate.assert_not_called()

if __name__ == "__main__":
    unittest.main()
