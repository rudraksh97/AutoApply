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

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

class MistralStructuredRunnable:
    """Runnable for Mistral structured output."""
    def __init__(self, client, model_name, schema):
        self.client = client
        self.model_name = model_name
        self.schema = schema

    async def ainvoke(self, prompt: str):
        messages = [{"role": "user", "content": prompt}]
        
        # Pydantic schema generation
        if hasattr(self.schema, "model_json_schema"):
            json_schema = self.schema.model_json_schema()
        else:
            json_schema = self.schema

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": getattr(self.schema, "__name__", "Schema"),
                "schema_definition": json_schema,
                "strict": True
            }
        }

        # Handle async call
        if hasattr(self.client.chat, "complete_async"):
            response = await self.client.chat.complete_async(
                model=self.model_name,
                messages=messages,
                response_format=response_format
            )
        else:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model_name,
                messages=messages,
                response_format=response_format
            )

        content = response.choices[0].message.content
        
        # Validate back to Pydantic object
        if hasattr(self.schema, "model_validate_json"):
            return self.schema.model_validate_json(content)
        return content

class MistralNativeWrapper:
    """Custom wrapper for Mistral SDK (Native)."""
    def __init__(self, api_key: str, model_name: str):
        if not Mistral:
            raise ImportError("mistralai package not found. Please install it.")
        
        self.client = Mistral(api_key=api_key)
        self.model_name = model_name

    def with_structured_output(self, schema):
        return MistralStructuredRunnable(self.client, self.model_name, schema)

    async def ainvoke(self, prompt: str):
        # Basic chat implementation
        messages = [{"role": "user", "content": prompt}]
        
        if hasattr(self.client.chat, "complete_async"):
            response = await self.client.chat.complete_async(
                model=self.model_name,
                messages=messages
            )
        else:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model_name,
                messages=messages
            )
            
        return response.choices[0].message.content

class MistralNativeBrowserUseAdapter:
    """
    Adapter to make native Mistral client compatible with browser-use (LangChain interface).
    Avoids ChatOpenAI wrapper which sends incompatible parameters (max_completion_tokens).
    """
    def __init__(self, api_key: str, model_name: str):
        if not Mistral:
            raise ImportError("mistralai package not found. Please install it.")
        self.client = Mistral(api_key=api_key)
        self.model_name = model_name
        self.model = model_name
        self.provider = "mistral"
        self.bound_tools = None

    def bind_tools(self, tools, **kwargs):
        """Mock bind_tools to capture tools for the next invoke."""
        logger.info(f"MistralAdapter: Binding {len(tools)} tools")
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages, config=None, **kwargs):
        # Convert LangChain messages to Mistral messages
        mistral_messages = []
        for msg in messages:
            role = "user"
            if hasattr(msg, "type"):
                if msg.type == "system": role = "system"
                elif msg.type == "ai": role = "assistant"
                elif msg.type == "tool": role = "tool"
            elif isinstance(msg, SystemMessage): role = "system"
            elif isinstance(msg, AIMessage): role = "assistant"
            
            # Simple content extraction
            content = msg.content if hasattr(msg, "content") else str(msg)
            
            # Handle tool usage in history
            message_data = {"role": role, "content": content}
            
            # If it's a ToolMessage, LangChain usually provides tool_call_id
            if role == "tool" and hasattr(msg, "tool_call_id"):
                 message_data["tool_call_id"] = msg.tool_call_id
                 # IMPORTANT: name is required for some providers but Mistral might just need tool_call_id
                 if hasattr(msg, "name"):
                     message_data["name"] = msg.name
            
            # If it's an Assistant message with tool_calls, we might need to reconstruct it 
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                 m_tool_calls = []
                 for tc in msg.tool_calls:
                     m_tool_calls.append({
                         "function": {
                             "name": tc.get("name"),
                             "arguments": json.dumps(tc.get("args", {}))
                         },
                         "id": tc.get("id", "call_default"),
                         "type": "function"
                     })
                 message_data["tool_calls"] = m_tool_calls
                 if not content: message_data["content"] = "" 
            
            mistral_messages.append(message_data)

        # Prepare request args
        request_args = {
            "model": self.model_name,
            "messages": mistral_messages
        }
        
        # Add tools if bound (from bind_tools) or passed in kwargs
        tools = kwargs.get("tools") or self.bound_tools
        if tools:
            # Mistral expects tools in a specific format.
            formatted_tools = []
            for t in tools:
                if isinstance(t, dict):
                    formatted_tools.append(t)
                elif hasattr(t, "to_openai_tool"): # LangChain tool
                     formatted_tools.append(t.to_openai_tool())
                else:
                     try:
                         formatted_tools.append(convert_to_openai_tool(t))
                     except:
                         pass
            
            if formatted_tools:
                request_args["tools"] = formatted_tools
                request_args["tool_choice"] = "auto"
                logger.debug(f"MistralAdapter: converted {len(formatted_tools)} tools for request")

        if hasattr(self.client.chat, "complete_async"):
            response = await self.client.chat.complete_async(**request_args)
        else:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.complete,
                **request_args
            )
            
        content = response.choices[0].message.content or ""
        msg = AIMessage(content=content)
        
        # Handle Tool Calls in Response
        if response.choices[0].message.tool_calls:
            lc_tool_calls = []
            for tc in response.choices[0].message.tool_calls:
                fn = tc.function
                args_str = fn.arguments
                
                # Parse JSON args
                try:
                    args_dict = json.loads(args_str) if isinstance(args_str, str) else args_str
                except:
                    args_dict = {}

                lc_tool_calls.append({
                    "name": fn.name,
                    "args": args_dict,
                    "id": tc.id,
                    "type": "tool_call"
                })
            
            msg.tool_calls = lc_tool_calls
            logger.info(f"MistralAdapter: returning {len(lc_tool_calls)} tool calls")
        else:
            logger.info(f"MistralAdapter: returning content (len={len(content)})")
        
        if hasattr(response, "usage"):
            # Match Browser-use / LangChain TokenUsageEntry schema
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "prompt_cached_tokens": 0,
                "prompt_cache_creation_tokens": 0,
                "prompt_image_tokens": 0
            }
            msg.usage = usage_dict
            msg.response_metadata = {"token_usage": usage_dict}

        # Fix for 'AIMessage' object has no attribute 'completion'
        msg.completion = msg.content
            
        return msg


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

    def __getattribute__(self, name):
        # Check our custom attributes first
        if name in ('real_llm', 'provider', 'config_id', 'model_name', 'model', '__class__', '__dict__', '__getattribute__'):
            return object.__getattribute__(self, name)
        
        # Delegate everything else to the real LLM
        real_llm = object.__getattribute__(self, 'real_llm')
        return getattr(real_llm, name)

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

def create_browser_use_llm(provider: str, model: str, api_key: str):
    """
    Create a browser-use compatible LLM wrapper.
    browser-use has its own LLM wrappers that handle message conversion.
    """
    if provider == "google":
        from browser_use.llm.google.chat import ChatGoogle
        return ChatGoogle(model=model, api_key=api_key, temperature=0.1)
    
    elif provider == "openrouter":
        # Use ChatOpenAI with OpenRouter base URL (more compatible)
        from browser_use.llm.openai.chat import ChatOpenAI
        
        # Claude models need special handling for structured output
        is_claude = "claude" in model.lower()
        
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
            # For Claude: add schema to system prompt instead of using response_format
            add_schema_to_system_prompt=is_claude,
            dont_force_structured_output=is_claude
        )
    
    elif provider == "cerebras":
        from browser_use.llm.cerebras.chat import ChatCerebras
        return ChatCerebras(model=model, api_key=api_key, temperature=0.1)

    elif provider == "mistral_sdk":
        # Native Mistral support via custom adapter
        return MistralNativeBrowserUseAdapter(
            api_key=api_key,
            model_name=model
        )
    
    else:
        # Fallback to OpenAI-compatible
        from browser_use.llm.openai.chat import ChatOpenAI as BrowserUseChatOpenAI
        return BrowserUseChatOpenAI(model=model, api_key=api_key, temperature=0.1)

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

        if provider == "mistral_sdk":
            llm = MistralNativeWrapper(
                api_key=api_key,
                model_name=model
            )

        elif provider == "google":
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
                    openai_api_key=api_key,
                    base_url="https://api.cerebras.ai/v1",
                    openai_api_base="https://api.cerebras.ai/v1",
                    temperature=0.1
                )
            
        elif provider == "openrouter":
            llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                openai_api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1
            )
            
        else: # openai_compatible
            base_url = "https://openrouter.ai/api/v1" if "openrouter" in model else None
            llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                openai_api_key=api_key,
                base_url=base_url,
                openai_api_base=base_url,
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
            api_key=config.get("api_key"),
            openai_api_key=config.get("api_key")
        )
        return adapt_llm(llm, "openai", config.get("id"), "gpt-3.5-turbo")

    # Backwards compatibility
    @classmethod
    def get_llm(cls):
        logger.warning("Legacy get_llm() called. Defaulting to 'Browser Automation' step.")
        return cls.get_llm_for_step("step_browser_automation")

