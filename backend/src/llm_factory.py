import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import ConfigManager
from src.token_manager import TokenManager

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory for creating LLM instances with intelligent load balancing.
    Selects the best available key for a given workflow step based on daily token usage.
    """

    @classmethod
    def get_llm_for_step(cls, step_id: str):
        """
        Returns an LLM instance optimized for the specific workflow step.
        
        Algorithm:
        1. Get all LLM configs linked to this step.
        2. Filter out keys that have exceeded their daily limit.
        3. Sort by (Limit - Used) descending -> "Highest Unused Tokens First".
        4. Return the top candidate.
        """
        cm = ConfigManager()
        tm = TokenManager()
        
        # 1. Get Linked Configs
        links = cm.get_workflow_links()
        linked_config_ids = [l["llm_config_id"] for l in links if l["workflow_id"] == step_id]
        
        if not linked_config_ids:
            logger.warning(f"No LLMs linked to step '{step_id}'. Falling back to any available free key.")
            return cls._get_fallback_llm(cm)

        all_configs = cm.get_user_configs()
        candidates = []
        
        for cfg in all_configs:
            if cfg["id"] in linked_config_ids:
                # 2. Check Limits
                limit = cfg.get("daily_token_limit", 0)
                used = cfg.get("tokens_used_today", 0)
                remaining = limit - used
                
                if remaining > 0:
                    candidates.append((remaining, cfg))
        
        if not candidates:
            logger.error(f"All linked LLMs for '{step_id}' are exhausted! Falling back.")
            return cls._get_fallback_llm(cm)
            
        # 3. Sort by Highest Remaining
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_config = candidates[0][1]
        
        logger.info(f"Selected LLM for '{step_id}': {best_config['name']} ({candidates[0][0]} tokens left)")
        
        return cls._create_llm_instance(best_config)

    @classmethod
    def _create_llm_instance(cls, config):
        """Creates the LangChain object from the config dict."""
        cm = ConfigManager()
        sdk_id = config.get("sdk_id")
        sdk = cm.get_sdk_definition(sdk_id)
        
        if not sdk:
            # Fallback for manual configs without SDK ref (shouldn't happen often)
            logger.warning(f"Config {config['name']} has invalid SDK ID {sdk_id}")
            return cls._create_generic_llm(config)

        provider = sdk.get("provider")
        model = sdk.get("model_name")
        api_key = config.get("api_key")

        # Wrapper to track usage on invoke logic? 
        # For now, we return the raw LangChain object, but ideally we wrap it to count tokens.
        # Since LangChain objects don't transparently support callback hooks for *our* specific logic easily 
        # without complex callback handlers, we assume the CALLER will report usage or we use a CallbackHandler.
        # To keep it simple, we just return the LLM. 
        # TODO: Add UsageTrackingCallbackHandler here.
        
        if provider == "google":
            return ChatGoogleGenerativeAI(
                model=model, 
                google_api_key=api_key, 
                temperature=0.3
            )
            
        elif provider == "cerebras":
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base="https://api.cerebras.ai/v1",
                temperature=0.3
            )
            
        elif provider == "openrouter":
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.3
            )
            
        else: # openai_compatible
            # Fallback for generic OpenAI compatible providers (e.g. self-hosted, other services)
            # If the user manually provided a base URL in the config, it would be passed here if we supported it.
            # For now, this defaults to OpenAI's standard API unless 'openrouter' is in the name (legacy check).
            base_url = "https://openrouter.ai/api/v1" if "openrouter" in model else None
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=0.3
            )

    @classmethod
    def _get_fallback_llm(cls, cm: ConfigManager):
        """Last resort fallback."""
        # Try to find *any* free key with credit
        all_configs = cm.get_user_configs()
        for cfg in all_configs:
            if cfg.get("plan_type") == "free":
                 return cls._create_llm_instance(cfg)
        
        # Absolute despair fallback (will likely fail if no keys)
        return ChatOpenAI(model="gpt-3.5-turbo")

    @classmethod
    def _create_generic_llm(cls, config):
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=config.get("api_key")
        )

    # Backwards compatibility for code not yet updated
    @classmethod
    def get_llm(cls):
        logger.warning("Legacy get_llm() called. Defaulting to 'Browser Automation' step.")
        return cls.get_llm_for_step("step_browser_automation")

