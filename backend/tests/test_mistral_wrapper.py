import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.llm_factory import create_browser_use_llm, LLMFactory

def test_create_browser_use_llm_mistral():
    """Verify create_browser_use_llm returns ChatMistral for mistral_sdk provider."""
    
    # Setup
    api_key = "test_key"
    model = "mistral-large-latest"
    provider = "mistral_sdk"
    
    # Patch the class where it is defined, which is what is imported inside the function
    with patch("browser_use.llm.mistral.ChatMistral") as MockChatMistral:
         # Act
        llm = create_browser_use_llm(provider, model, api_key)
        
        # Assert
        MockChatMistral.assert_called_with(
            model=model,
            api_key=api_key,
            temperature=0.1
        )
        # create_browser_use_llm returns the instance directly
        assert llm == MockChatMistral.return_value

        
def test_create_llm_instance_mistral():
    """Verify _create_llm_instance returns ChatMistral for mistral_sdk provider."""
    
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
        
        with patch("browser_use.llm.mistral.ChatMistral") as MockChatMistral:
            
            # Act
            llm = LLMFactory._create_llm_instance(config)
            
            # Assert
            MockChatMistral.assert_called_with(
                model="mistral-large-latest",
                api_key="test_key",
                temperature=0.1
            )
            # _create_llm_instance wraps the LLM in PrincipalLLMAdapter
            # So llm is the adapter, and llm.real_llm is the mock
            assert llm.real_llm == MockChatMistral.return_value
            assert llm.provider == "mistral_sdk"
