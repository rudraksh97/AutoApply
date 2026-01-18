import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_cerebras import ChatCerebras
except ImportError:
    ChatCerebras = None
    
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
                # 2. Check Limits (Dynamic from SDK)
                sdk_id = cfg.get("sdk_id")
                sdk = cm.get_sdk_definition(sdk_id)
                limit = sdk.get("daily_token_limit", 1000000) if sdk else 1000000
                
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
            logger.warning(f"Config {config['name']} has invalid SDK ID {sdk_id}")
            return cls._create_generic_llm(config)

        provider = sdk.get("provider", "openai_compatible")
        model = sdk.get("model_name")
        api_key = config.get("api_key")
        
        llm = None

        if provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=model, 
                google_api_key=api_key, 
                temperature=0.1
            )
            
        elif provider == "cerebras":
            if ChatCerebras:
                # Cerebras SDK picks up key from env if not passed, but we pass it explicitly here if supported
                # Note: langchain_cerebras might expect env var CEREBRAS_API_KEY
                # We sets the env var temporarily or pass it if constructor allows
                # Checking constructor signature usually allows api_key.
                # Assuming standard langchain pattern:
                llm = ChatCerebras(
                    model=model,
                    api_key=api_key,
                    temperature=0.1
                )
            else:
                 # Fallback if library missing
                logger.error("langchain_cerebras not installed. Falling back to OpenAI compatible.")
                llm = ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    openai_api_base="https://api.cerebras.ai/v1",
                    temperature=0.1
                )
            
        elif provider == "openrouter":
            llm = ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1
            )
            
        else: # openai_compatible
            base_url = "https://openrouter.ai/api/v1" if "openrouter" in model else None
            llm = ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=0.1
            )
            
        # CRITICAL FIX: Attach provider attribute to prevent AttributeError in downstream agents
        # Also attach config_id for credit usage tracking
        if llm:
            llm.provider = provider
            llm.config_id = config.get("id")
            
        return llm

    @classmethod
    def _get_fallback_llm(cls, cm: ConfigManager):
        """Last resort fallback."""
        all_configs = cm.get_user_configs()
        for cfg in all_configs:
            if cfg.get("plan_type") == "free":
                 return cls._create_llm_instance(cfg)
        
        fallback = ChatOpenAI(model="gpt-3.5-turbo")
        fallback.provider = "openai"
        return fallback

    @classmethod
    def _create_generic_llm(cls, config):
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=config.get("api_key")
        )
        llm.provider = "openai"
        return llm

    # Backwards compatibility
    @classmethod
    def get_llm(cls):
        logger.warning("Legacy get_llm() called. Defaulting to 'Browser Automation' step.")
        return cls.get_llm_for_step("step_browser_automation")

