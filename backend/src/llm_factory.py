import os
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import ConfigManager

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory for creating LLM instances based on the current plan and configuration.
    Supports round-robin selection for the free plan.
    """
    _last_index = -1

    @classmethod
    def get_llm(cls):
        """
        Returns an LLM instance based on the current configuration.
        """
        cm = ConfigManager()
        plan_type = cm.get_plan_type()

        if plan_type == "paid":
            return cls._get_paid_llm(cm)
        else:
            return cls._get_free_llm(cm)

    @classmethod
    def _get_paid_llm(cls, cm: ConfigManager):
        """Returns the OpenRouter LLM for the paid plan."""
        model = cm.get_selected_model()
        api_key = cm.get_api_key("OPENROUTER_API_KEY")
        
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3
        )

    @classmethod
    def _get_free_llm(cls, cm: ConfigManager):
        """Returns a free LLM using round-robin selection."""
        configs = cm.get_free_configs()
        
        if not configs:
            logger.warning("No free LLM configurations found. Falling back to default OpenRouter free model.")
            return ChatOpenAI(
                model="google/gemini-2.0-flash-001", # Default fallback
                openai_api_key=cm.get_api_key("OPENROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.3
            )

        # Round-robin selection
        cls._last_index = (cls._last_index + 1) % len(configs)
        config = configs[cls._last_index]
        
        sdk = config["sdk"]
        model = config["model"]
        api_key = config["api_key"]

        if sdk == "google":
            return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0.3)
        elif sdk == "cerebras":
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base="https://api.cerebras.ai/v1",
                temperature=0.3
            )
        else: # openai_compatible
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                temperature=0.3
            )
