try:
    from browser_use.llm.cerebras.chat import ChatCerebras
    print("Successfully imported ChatCerebras")
    print(f"ChatCerebras type: {ChatCerebras}")
    print(f"ChatCerebras bases: {ChatCerebras.__bases__}")
    # Inspect if it has special methods
    import inspect
    print(dir(ChatCerebras))
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
