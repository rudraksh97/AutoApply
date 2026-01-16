"""Visual/manual test for browser-based form extraction.

This test runs a real browser (headed mode) to visually verify form extraction.
Intended for manual testing, not CI.
"""

import pytest

from src.agent import BrowserAgent


# Default test URL - can be overridden via environment
TEST_JOB_URL = "https://jobs.ashbyhq.com/Framenergy/d8b6bae9-cd1b-4dea-8d98-168dad8f2294/application"


@pytest.mark.asyncio
async def test_visual_form_extraction():
    """
    Visual test for form extraction.

    Launches a headed browser to extract form fields from a job application page.
    Watch the browser window to verify the agent's behavior.

    This test is skipped in CI - run manually with:
        pytest tests/test_visual_apply.py -v -s
    """
    print(f"\n[VISUAL TEST] Starting Form Extraction...")
    print(f"Job URL: {TEST_JOB_URL}")
    print("Watch the browser window...")

    # Initialize agent in headed mode for visual verification
    agent = BrowserAgent(headless=False)

    # Run form extraction
    result = await agent.extract_form(TEST_JOB_URL)

    print(f"\n[VISUAL TEST] Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Fields found: {len(result.get('fields', []))}")

    if result.get('fields'):
        print("\n  Extracted fields:")
        for field in result['fields'][:5]:  # Show first 5
            print(f"    - {field.get('label', 'N/A')} ({field.get('field_type', 'unknown')})")

    assert result is not None, "Agent returned None"
    assert "fields" in result, "Result should contain 'fields' key"
