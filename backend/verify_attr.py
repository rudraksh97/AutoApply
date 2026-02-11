
try:
    from langchain_mistralai import ChatMistralAI
    llm = ChatMistralAI(api_key="test", model="test")
    try:
        llm.provider = "mistral"
        print(f"Successfully set provider: {llm.provider}")
    except Exception as e:
        print(f"Failed to set provider directly: {e}")
        
    # Check if we can patch it
    class MistralWrapper(ChatMistralAI):
        @property
        def provider(self):
            return "mistral"
            
    llm2 = MistralWrapper(api_key="test", model="test")
    print(f"Wrapper provider: {llm2.provider}")
    
except ImportError:
    print("langchain_mistralai not installed")
except Exception as e:
    print(f"General Error: {e}")
