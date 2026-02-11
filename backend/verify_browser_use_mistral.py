
try:
    from browser_use.llm.mistral import ChatMistral
    print("Successfully imported ChatMistral from browser_use.llm.mistral")
    llm = ChatMistral(api_key="test", model_name="test") # Check init args
    print(f"LLM created. Provider: {getattr(llm, 'provider', 'Not Found')}")
    print(f"LLM type: {type(llm)}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
