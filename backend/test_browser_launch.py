import asyncio
import os
import sys
from browser_use import Browser
from playwright.async_api import async_playwright

async def test_playwright_direct():
    print("\n--- Testing Playwright Direct ---")
    try:
        async with async_playwright() as p:
            print("Playwright initialized.")
            print(f"Browsers installed at: {p.chromium.executable_path}")
            
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            print("Chromium launched successfully (direct).")
            await browser.close()
            print("Chromium closed (direct).")
    except Exception as e:
        print(f"ERROR (Direct Playwright): {e}")
        import traceback
        traceback.print_exc()

async def test_browser_use():
    print("\n--- Testing Browser Use Library ---")
    browser_config = {
        "headless": True,
        "chromium_sandbox": False,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]
    }
    
    print(f"Config: {browser_config}")
    
    try:
        browser = Browser(**browser_config)
        print("Browser (browser-use) initialized object.")
        
        # This triggers the actual launch usually
        print("Starting new context...")
        context = await browser.new_context()
        print(f"Context created: {context}")
        
        print("Getting page...")
        page = await context.get_page()
        print("Page opened.")
        
        print("Closing browser...")
        await browser.close()
        print("Closed.")
        
    except Exception as e:
        print(f"ERROR (browser-use): {e}")
        import traceback
        traceback.print_exc()

async def main():
    print(f"Python: {sys.version}")
    await test_playwright_direct()
    await test_browser_use()

if __name__ == "__main__":
    asyncio.run(main())
