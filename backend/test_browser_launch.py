import asyncio
import os
import sys
from browser_use import Browser, Agent
from playwright.async_api import async_playwright
from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel

class MockLLM(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("Mock LLM")
    
    @property
    def _llm_type(self):
        return "mock"
        
    async def ainvoke(self, *args, **kwargs):
        return AIMessage(content="{'action': {'done': {'text': 'done'}}}")

async def test_connect_to_existing():
    print("\n--- Testing Connection to Existing Browser ---")
    
    async with async_playwright() as p:
        # 1. Launch Browser Manually with Debugging Port
        print("Launching Chrome manually...")
        browser_app = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--remote-debugging-port=9222" 
            ]
        )
        print("Chrome launched on port 9222.")
        
        try:
            # 2. Initialize Browser-Use with CDP URL
            cdp_url = "http://localhost:9222"
            browser = Browser(cdp_url=cdp_url)
            print(f"Browser-Use object initialized with {cdp_url}")
            
            # 3. Initialize Agent
            agent = Agent(
                task="Go to google.com",
                llm=MockLLM(),
                browser=browser,
            )
            print("Agent initialized.")
            
            # 4. Run Agent
            print("Running agent...")
            await agent.run()
            print("Agent run finished successfully!")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser_app.close()
            print("Manual browser closed.")

async def main():
    print(f"Python: {sys.version}")
    await test_connect_to_existing()

if __name__ == "__main__":
    asyncio.run(main())
