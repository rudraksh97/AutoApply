
from langchain_openai import ChatOpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chat_openai_attrs():
    print("--- Testing ChatOpenAI Attributes ---")
    llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key="dummy")
    print(f"Type: {type(llm)}")
    
    attrs_to_check = ['model', 'model_name', 'provider']
    for attr in attrs_to_check:
        try:
            val = getattr(llm, attr)
            print(f"Attribute '{attr}': {val}")
        except AttributeError:
            print(f"Attribute '{attr}' NOT FOUND")

    # Check the adapter too
    from backend.src.llm_factory import PrincipalLLMAdapter
    adapter = PrincipalLLMAdapter(llm, provider="openai", config_id="test", model_name="gpt-3.5-turbo")
    print(f"\n--- Testing Adapter Attributes ---")
    for attr in attrs_to_check:
        try:
            val = getattr(adapter, attr)
            print(f"Attribute '{attr}': {val}")
        except AttributeError:
            print(f"Attribute '{attr}' NOT FOUND")

if __name__ == "__main__":
    test_chat_openai_attrs()
