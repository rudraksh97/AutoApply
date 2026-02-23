import logging
import re
from typing import Optional
from urllib.parse import urlparse
from src.llm_factory import LLMFactory
from src.prompts import EXTRACT_JOB_LINK_FROM_RSS_PROMPT
from src.schemas import RSSLinkExtractionOutput

logger = logging.getLogger(__name__)

# Patterns that indicate we need LLM extraction (feed links to aggregator, not jobs)
AGGREGATOR_FEED_PATTERNS = [
    "hnrss.org",
    "news.ycombinator.com",
    "reddit.com",
    "lobste.rs",
]

# Test feed URL pattern to skip during "Poll All"
TEST_FEED_PATTERN = "/test/feed.xml"

def needs_llm_extraction(feed_url: str) -> bool:
    """Check if this feed needs LLM-based job link extraction."""
    return any(pattern in feed_url.lower() for pattern in AGGREGATOR_FEED_PATTERNS)


async def extract_job_link_with_llm(entry: dict, user_id: Optional[str] = None) -> dict:
    """
    Use LLM to extract the actual job application URL from an RSS entry using structured output.
    
    Returns dict with components of RSSLinkExtractionOutput.
    """
    # Get entry content
    entry_title = entry.get("title", "")
    entry_link = entry.get("link", "")
    entry_description = entry.get("description", "") or entry.get("summary", "")
    
    if not entry_description and entry.get("content"):
        content_list = entry.get("content", [])
        if content_list and len(content_list) > 0:
            entry_description = content_list[0].get("value", "")
    
    # Build prompt
    prompt = EXTRACT_JOB_LINK_FROM_RSS_PROMPT.format(
        entry_title=entry_title,
        entry_description=entry_description[:3000],
        entry_link=entry_link
    )
    
    try:
        llm = LLMFactory.get_llm_for_step("step_rss_link_extraction", user_id=user_id)
        
        # Deduct credits
        from src.token_manager import TokenManager
        config_id = getattr(llm, "config_id", None)
        if config_id:
            TokenManager().deduct_credits(config_id, len(prompt) * 2)

        # Use structured output
        structured_llm = llm.with_structured_output(RSSLinkExtractionOutput)
        result = await structured_llm.ainvoke(prompt)
        
        # Return as dict for compatibility
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"LLM RSS extraction failed: {e}\nStack trace:\n{tb}")
        return {
            "job_url": entry_link, # Fallback to original
            "job_title": entry_title,
            "location": None,
            "confidence": 0.0,
            "notes": f"LLM error: {str(e)}"
        }
