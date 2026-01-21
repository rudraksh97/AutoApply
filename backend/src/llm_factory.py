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

class PrincipalLLMAdapter:
    """
    Principal Engineer solution: Transparent Proxy.
    This class does NOT inherit from BaseChatModel to avoid Pydantic corruption.
    Instead, it uses the __class__ property hack to satisfy isinstance(proxy, BaseChatModel).
    """
    def __init__(self, real_llm, provider, config_id, model_name):
        # Use __dict__ directly to avoid any potential __setattr__ logic
        self.__dict__['real_llm'] = real_llm
        self.__dict__['provider'] = provider
        self.__dict__['config_id'] = config_id
        self.__dict__['model_name'] = model_name
        self.__dict__['model'] = model_name # Alias for browser-use compatibility

    @property
    def __class__(self):
        # This hack makes isinstance(adapter, BaseChatModel) True
        return self.real_llm.__class__

    def __getattr__(self, name):
        # Delegate everything to the real LLM
        return getattr(self.real_llm, name)

    def __dir__(self):
        # Ensure our extra attributes show up in dir()
        return list(set(dir(self.real_llm) + ['provider', 'config_id', 'model_name', 'model']))

    def __repr__(self):
        return f"PrincipalLLMAdapter(provider={self.provider}, model={self.model_name}, real_llm={repr(self.real_llm)})"

def adapt_llm(llm, provider: str, config_id: str, model_name: str):
    """
    Wraps the LLM in a Transparent PrincipalLLMAdapter.
    """
    if not llm:
        return llm
    
    # Avoid double-wrapping
    if isinstance(llm, PrincipalLLMAdapter):
        return llm
        
    logger.info(f"Wrapping {type(llm).__name__} in Transparent PrincipalLLMAdapter for '{provider}'")
    
    # Update internal metadata as well for redundancy
    if hasattr(llm, 'metadata'):
        meta = {"provider": provider, "config_id": config_id, "model_name": model_name}
        if llm.metadata is None:
            llm.metadata = meta
        else:
            llm.metadata.update(meta)
            
    return PrincipalLLMAdapter(
        real_llm=llm,
        provider=provider,
        config_id=config_id,
        model_name=model_name
    )

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
            # Check if this is a known internal step and log it
            internal_steps = [
                "step_browser_automation", 
                "step_form_answering", 
                "step_ats_scoring", 
                "step_resume_tailoring",
                "step_rss_link_extraction",
                "step_resume_parsing"
            ]
            if step_id in internal_steps:
                 logger.warning(f"No LLMs linked to internal step '{step_id}'. Falling back.")
            else:
                 logger.warning(f"Unknown step '{step_id}'. Falling back.")
                 
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
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.1
            )
            
        elif provider == "cerebras":
            if ChatCerebras:
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
                    api_key=api_key,
                    base_url="https://api.cerebras.ai/v1",
                    temperature=0.1
                )
            
        elif provider == "openrouter":
            llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.1
            )
            
        else: # openai_compatible
            base_url = "https://openrouter.ai/api/v1" if "openrouter" in model else None
            llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=0.1
            )
            
        # Unified Adaptation Pattern (Decorator Pattern)
        return adapt_llm(llm, provider, config.get("id"), model)

    @classmethod
    def _get_fallback_llm(cls, cm: ConfigManager):
        """Last resort fallback."""
        all_configs = cm.get_user_configs()
        for cfg in all_configs:
            if cfg.get("plan_type") == "free":
                 return cls._create_llm_instance(cfg)
        
        fallback = ChatOpenAI(model="gpt-3.5-turbo")
        return adapt_llm(fallback, "openai", "fallback", "gpt-3.5-turbo")

    @classmethod
    def _create_generic_llm(cls, config):
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=config.get("api_key")
        )
        return adapt_llm(llm, "openai", config.get("id"), "gpt-3.5-turbo")

    # Backwards compatibility
    @classmethod
    def get_llm(cls):
        logger.warning("Legacy get_llm() called. Defaulting to 'Browser Automation' step.")
        return cls.get_llm_for_step("step_browser_automation")

