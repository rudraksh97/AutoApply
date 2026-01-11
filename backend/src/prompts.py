"""
Centralized repository for AI/LLM prompts used across the application.
"""

SCRAPE_JOB_TASK_TEMPLATE = """
Go to {job_link}.
Extract the full job description, responsibilities, and requirements.
Return the result as a structured string.
"""

APPLY_JOB_TASK_TEMPLATE = """
Go to {job_link}.
Find the 'Apply' button and click it to open the application form.
Fill out the application form with the following details:
{user_details}

When asked for a resume, upload the local file found at: {abs_resume_path}

If there is a submit button, click it. 
Confirm if the application was submitted successfully.
"""

RESUME_OPTIMIZER_PROMPT_TEMPLATE = """
You are an expert ATS optimizer.
Analyze the Job Description and extract the most important technical keywords, skills, and tools mentioned.

Job Description:
{job_description}

Return a JSON object with a single key:
- skills_list: A list of the top 10-15 most relevant keywords/skills found in the description.

Do not manufacture skills that are completely unrelated to software engineering, but prioritize matching the JD hard skills.
"""
