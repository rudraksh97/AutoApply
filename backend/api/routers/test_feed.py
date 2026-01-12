"""
Test RSS Feed for development and testing.
Provides a RSS feed with real job postings to verify the system works end-to-end.
"""

from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime, timedelta

router = APIRouter(prefix="/test", tags=["Testing"])

# Real job postings for testing
TEST_JOBS = [
    {
        "title": "Software Engineer at Framenergy",
        "link": "https://jobs.ashbyhq.com/Framenergy/d8b6bae9-cd1b-4dea-8d98-168dad8f2294",
        "company": "Framenergy",
        "description": "Join Framenergy to work on innovative energy solutions.",
    },
    {
        "title": "Role at Pear VC",
        "link": "https://jobs.ashbyhq.com/Pear-VC/eeb2d80c-a65e-4318-b769-1c88b026cbc4/application",
        "company": "Pear VC",
        "description": "Join Pear VC, a leading early-stage venture capital firm.",
    },
]


def generate_job_item(job: dict, index: int) -> str:
    """Generate a single RSS item for a job posting."""
    pub_date = (datetime.now() - timedelta(hours=index)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    return f"""
    <item>
      <title>{job['title']}</title>
      <link>{job['link']}</link>
      <guid isPermaLink="true">{job['link']}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[
        <p><strong>Company:</strong> {job['company']}</p>
        <p>{job['description']}</p>
      ]]></description>
      <category>Engineering</category>
      <category>Full-time</category>
    </item>"""


@router.get("/feed.xml", response_class=Response)
def get_test_rss_feed():
    """
    Returns a test RSS feed with real job postings from Ashby.
    
    Usage:
        Add this URL to your RSS feeds: http://localhost:8000/test/feed.xml
    """
    base_url = "http://localhost:8000"
    
    # Generate job items from real jobs
    items = "\n".join(generate_job_item(job, i) for i, job in enumerate(TEST_JOBS))
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AutoApply Test Job Feed</title>
    <link>{base_url}/test/feed.xml</link>
    <description>A test RSS feed with real job postings for testing AutoApply</description>
    <language>en-us</language>
    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
    <atom:link href="{base_url}/test/feed.xml" rel="self" type="application/rss+xml"/>
    {items}
  </channel>
</rss>"""
    
    return Response(
        content=rss_content,
        media_type="application/rss+xml",
        headers={"Content-Type": "application/rss+xml; charset=utf-8"}
    )


@router.get("/status")
def get_test_status():
    """
    Returns the status of the test feed system.
    Useful for verifying the backend is running correctly.
    """
    return {
        "status": "ok",
        "message": "Test feed system is operational",
        "feed_url": "http://localhost:8000/test/feed.xml",
        "jobs": [job["link"] for job in TEST_JOBS],
        "instructions": [
            "1. Go to Feeds page in the UI",
            "2. Click Poll on the Test Feed section",
            "3. The system will add these real job postings",
            "4. Jobs link to real Ashby application pages"
        ]
    }
