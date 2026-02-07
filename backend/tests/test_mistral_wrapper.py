import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Mock mistralai and langchain_mistralai before importing llm_factory
sys.modules["mistralai"] = MagicMock()
sys.modules["langchain_mistralai"] = MagicMock()

from src.llm_factory import create_browser_use_llm, LLMFactory

def test_create_browser_use_llm_mistral():
    """Verify create_browser_use_llm returns ChatMistralAI for mistral_sdk provider."""
    
    # Setup
    api_key = "test_key"
    model = "mistral-large-latest"
    provider = "mistral_sdk"
    
    with patch("src.llm_factory.ChatMistralAI") as MockChatMistral:
        # Act
        llm = create_browser_use_llm(provider, model, api_key)
        
        # Assert
        MockChatMistral.assert_called_with(
            model=model,
            api_key=api_key,
            temperature=0.1
        )
        assert llm.provider == "mistral"

def test_create_llm_instance_mistral():
    """Verify _create_llm_instance returns ChatMistralAI for mistral_sdk provider."""
    
    # Setup
    config = {
        "id": "test_config",
        "sdk_id": "mistral_sdk", 
        "name": "Mistral Test",
        "api_key": "test_key"
    }
    
    # Mock ConfigManager to return definition
    with patch("src.llm_factory.ConfigManager") as MockCM:
        mock_cm = MockCM.return_value
        mock_cm.get_sdk_definition.return_value = {
            "provider": "mistral_sdk",
            "model_name": "mistral-large-latest"
        }
        
        with patch("src.llm_factory.ChatMistralAI") as MockChatMistral:
            # Act
            # Access private method for testing logic
            LLMFactory._create_llm_instance(config)
            
            # Assert
            MockChatMistral.assert_called_with(
                model="mistral-large-latest",
                api_key="test_key",
                temperature=0.1
            )
            # We can't easily check the return value of _create_llm_instance here since it mocks the class
            # But the code path is covered by test_create_browser_use_llm_mistral which calls the same logic/factory pattern usually
            # Actually, _create_llm_instance returns the instance, need capture it
            
            # Re-running the act to capture return
            llm = LLMFactory._create_llm_instance(config)
            assert llm.provider == "mistral"
