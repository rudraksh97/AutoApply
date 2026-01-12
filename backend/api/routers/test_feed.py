"""
Test RSS Feed for development and testing.
Provides a dummy RSS feed with sample job postings to verify the system works end-to-end.
"""

from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/test", tags=["Testing"])

# Sample job data for generating test feeds
SAMPLE_COMPANIES = [
    ("Acme Corp", "San Francisco, CA"),
    ("TechStart Inc", "New York, NY"),
    ("DataFlow Systems", "Austin, TX"),
    ("CloudNine Solutions", "Seattle, WA"),
    ("Quantum Labs", "Boston, MA"),
    ("InnovateTech", "Denver, CO"),
    ("ByteWorks", "Portland, OR"),
    ("FutureSoft", "Chicago, IL"),
]

SAMPLE_ROLES = [
    "Senior Software Engineer",
    "Full Stack Developer",
    "Backend Engineer",
    "Frontend Developer",
    "DevOps Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Platform Engineer",
    "Site Reliability Engineer",
    "Software Architect",
]

SAMPLE_DESCRIPTIONS = [
    "We're looking for a passionate engineer to join our growing team.",
    "Help us build the next generation of cloud infrastructure.",
    "Join a fast-paced startup working on cutting-edge technology.",
    "Work with a talented team on challenging problems at scale.",
    "Be part of our mission to revolutionize the industry.",
]


def generate_job_item(index: int, base_url: str) -> str:
    """Generate a single RSS item for a job posting."""
    # Use deterministic selection based on index (not random)
    company, location = SAMPLE_COMPANIES[index % len(SAMPLE_COMPANIES)]
    role = SAMPLE_ROLES[index % len(SAMPLE_ROLES)]
    description = SAMPLE_DESCRIPTIONS[index % len(SAMPLE_DESCRIPTIONS)]
    
    # Generate a stable unique ID based on index only (not date)
    job_id = f"test-job-{index:03d}"
    pub_date = (datetime.now() - timedelta(hours=index)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    return f"""
    <item>
      <title>{role} at {company}</title>
      <link>{base_url}/test/job/{job_id}</link>
      <guid isPermaLink="false">{job_id}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Location:</strong> {location}</p>
        <p><strong>Role:</strong> {role}</p>
        <p>{description}</p>
        <p>Requirements: 3+ years experience, strong problem-solving skills, excellent communication.</p>
      ]]></description>
      <category>Engineering</category>
      <category>Full-time</category>
    </item>"""


@router.get("/feed.xml", response_class=Response)
def get_test_rss_feed(count: int = 5):
    """
    Returns a test RSS feed with sample job postings.
    
    Args:
        count: Number of job postings to include (default: 5, max: 20)
    
    Usage:
        Add this URL to your RSS feeds: http://localhost:8000/test/feed.xml
    """
    count = min(max(1, count), 20)  # Clamp between 1 and 20
    base_url = "http://localhost:8000"
    
    # Generate job items
    items = "\n".join(generate_job_item(i, base_url) for i in range(count))
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AutoApply Test Job Feed</title>
    <link>{base_url}/test/feed.xml</link>
    <description>A test RSS feed with sample job postings for testing AutoApply</description>
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


@router.get("/job/{job_id}")
def get_test_job_page(job_id: str):
    """
    Returns a simple test job application page.
    This simulates a real job posting page that the browser agent would interact with.
    """
    # Extract index from job_id for deterministic content
    try:
        index = int(job_id.split("-")[-1])
    except (ValueError, IndexError):
        index = hash(job_id) % 100
    
    company, location = SAMPLE_COMPANIES[index % len(SAMPLE_COMPANIES)]
    role = SAMPLE_ROLES[index % len(SAMPLE_ROLES)]
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{role} - {company}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 40px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .company {{ font-size: 18px; opacity: 0.9; }}
        .header .meta {{ margin-top: 16px; font-size: 14px; opacity: 0.7; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 32px; }}
        .section h2 {{ 
            font-size: 18px; 
            color: #1a1a2e; 
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }}
        .section p, .section li {{ 
            color: #4a5568; 
            line-height: 1.7;
            margin-bottom: 8px;
        }}
        .section ul {{ padding-left: 24px; }}
        .apply-form {{ 
            background: #f7fafc; 
            padding: 32px; 
            border-radius: 12px;
            margin-top: 32px;
        }}
        .form-group {{ margin-bottom: 20px; }}
        .form-group label {{ 
            display: block; 
            font-weight: 600; 
            margin-bottom: 8px;
            color: #2d3748;
        }}
        .form-group input, .form-group textarea, .form-group select {{ 
            width: 100%; 
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }}
        .form-group input:focus, .form-group textarea:focus {{ 
            outline: none;
            border-color: #667eea;
        }}
        .form-group textarea {{ resize: vertical; min-height: 120px; }}
        .btn {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .btn:hover {{ 
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }}
        .test-badge {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f56565;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="test-badge">🧪 TEST PAGE</div>
    <div class="container">
        <div class="header">
            <h1>{role}</h1>
            <div class="company">{company}</div>
            <div class="meta">📍 {location} • 💼 Full-time • 💰 Competitive</div>
        </div>
        <div class="content">
            <div class="section">
                <h2>About the Role</h2>
                <p>We're looking for an experienced {role} to join our team at {company}. 
                You'll work on challenging problems and help us build innovative solutions.</p>
            </div>
            
            <div class="section">
                <h2>Requirements</h2>
                <ul>
                    <li>3+ years of relevant experience</li>
                    <li>Strong problem-solving and analytical skills</li>
                    <li>Experience with modern development practices</li>
                    <li>Excellent communication and collaboration abilities</li>
                    <li>Bachelor's degree in Computer Science or equivalent</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>Benefits</h2>
                <ul>
                    <li>Competitive salary and equity</li>
                    <li>Health, dental, and vision insurance</li>
                    <li>Flexible work arrangements</li>
                    <li>Professional development budget</li>
                    <li>401(k) matching</li>
                </ul>
            </div>
            
            <div class="apply-form">
                <h2>Apply Now</h2>
                <form id="application-form">
                    <div class="form-group">
                        <label for="full_name">Full Name *</label>
                        <input type="text" id="full_name" name="full_name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="phone">Phone Number</label>
                        <input type="tel" id="phone" name="phone">
                    </div>
                    <div class="form-group">
                        <label for="linkedin">LinkedIn Profile</label>
                        <input type="url" id="linkedin" name="linkedin" placeholder="https://linkedin.com/in/...">
                    </div>
                    <div class="form-group">
                        <label for="experience">Years of Experience *</label>
                        <select id="experience" name="experience" required>
                            <option value="">Select...</option>
                            <option value="0-2">0-2 years</option>
                            <option value="3-5">3-5 years</option>
                            <option value="5-10">5-10 years</option>
                            <option value="10+">10+ years</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="cover_letter">Cover Letter</label>
                        <textarea id="cover_letter" name="cover_letter" placeholder="Tell us why you'd be a great fit..."></textarea>
                    </div>
                    <button type="submit" class="btn">Submit Application</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('application-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            alert('✅ Test application submitted successfully!\\n\\nThis is a test page - no actual application was sent.');
        }});
    </script>
</body>
</html>"""
    
    return Response(content=html_content, media_type="text/html")


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
        "instructions": [
            "1. Go to Settings > Feeds in the UI",
            "2. Add this URL: http://localhost:8000/test/feed.xml",
            "3. The system will poll this feed and create jobs",
            "4. Each job links to a test application page"
        ]
    }
