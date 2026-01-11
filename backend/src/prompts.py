"""
Centralized repository for AI/LLM prompts used across the application.
"""

FORM_FILLING_CONTEXT = """
When filling web forms:
- Always wait for page elements to fully load before interacting
- Click directly on input fields before typing to ensure focus
- For text fields, clear any existing text before entering new values
- For dropdowns/select elements, click to open then click the matching option
- For radio buttons and checkboxes, click directly on the option
- If a field seems unresponsive, scroll it into view and try clicking again
- After filling a field, verify the value was entered correctly
- Handle file uploads by clicking the upload button/area and selecting the file
- Look for and dismiss any cookie consent or pop-up dialogs that may block the form

IMPORTANT - DO NOT GIVE UP EASILY:
- If an action fails, try a different approach
- If you encounter an error, analyze it and try to fix it
- Keep trying different strategies until you succeed or have exhausted all options
- Only report failure after trying at least 3 different approaches

CRITICAL - LOCATION AUTOCOMPLETE FIELDS (e.g., on Ashby job forms):
1. Click on the location input field to focus it
2. Type a city name like "New York" or "Buffalo"
3. WAIT for 2 seconds - autocomplete suggestions need time to load
4. After waiting, look for a dropdown list of city suggestions
5. Click on one of the suggested cities from the dropdown
6. DO NOT just type text - you MUST click a suggestion from the dropdown
7. If no suggestions appear, try typing just "New" and wait again
"""

SCRAPE_JOB_TASK_TEMPLATE = """
Go to {job_link}.
Extract the full job description, responsibilities, and requirements.
Return the result as a structured string.
"""

PREFILL_JOB_TASK_TEMPLATE = """
You are a job application assistant. Your task is to PREPARE a job application form but NEVER submit it.

TASK: Prefill the job application at {job_link}

===== APPLICANT INFORMATION =====
{user_details}

===== RESUME FILE =====
Upload this file when asked for resume: {abs_resume_path}

===== CRITICAL CONSTRAINT =====
⚠️ DO NOT SUBMIT THE APPLICATION ⚠️
⚠️ DO NOT CLICK ANY SUBMIT, APPLY, OR SEND BUTTON ⚠️
Your job is ONLY to fill the form. The user will review and submit manually later.

===== STRATEGY: USE RESUME AUTOFILL FIRST =====
Many job sites can auto-fill fields from your resume. Use this to save time!

STEP 1 - NAVIGATE:
Go to {job_link}. Wait for the page to fully load.

STEP 2 - FIND & PRIORITIZE RESUME UPLOAD:
FIRST, look for a resume upload field or "Autofill from resume" / "Parse resume" button.
- Upload the resume file FIRST: {abs_resume_path}
- Wait 2-3 seconds for the site to parse the resume
- Many fields may auto-populate from the resume

STEP 3 - VALIDATE AUTOFILLED DATA:
After resume upload, check each pre-filled field:
- Compare with the APPLICANT INFORMATION above
- If autofilled data matches profile data → Leave it
- If autofilled data is WRONG → Clear and enter correct value
- If a field is still EMPTY → Fill it manually

STEP 4 - FILL REMAINING EMPTY FIELDS:
For each input field you encounter:
a) Identify the field's label or placeholder text
b) Match it to the applicant information above
c) Click the field, clear any existing text, then type the value

Common field mappings:
- "First Name", "Given Name" → Use first_name value
- "Last Name", "Surname", "Family Name" → Use last_name value  
- "Full Name", "Name" → Use full_name value
- "Email", "Email Address" → Use email value
- "Phone", "Phone Number", "Mobile", "Cell" → Use phone value
- "LinkedIn", "LinkedIn URL", "LinkedIn Profile" → Use linkedin value
- "GitHub", "GitHub URL", "GitHub Profile" → Use github value
- "Portfolio", "Website", "Personal Website" → Use portfolio value
- "Location", "City", "Address" → Use location value
- "Gender" → Use gender value
- "Race", "Ethnicity", "Race/Ethnicity" → Use race value
- "Veteran", "Veteran Status" → Use veteran_status value
- "Disability", "Disability Status" → Use disability_status value
- "Authorized to work", "Work Authorization" → Use authorized_to_work value
- "Sponsorship", "Require Sponsorship", "Will you require sponsorship" → Use requires_sponsorship value
- "Willing to relocate", "Open to relocation", "Can you relocate", "Would you relocate", "Relocation" → ALWAYS select "Yes" or "True" - NEVER select "No" or "False"
- "Why are you interested", "Why this company", "Why do you want to work here" → Use why_us value
- "Why are you a good fit", "Tell us about yourself", "Cover letter" → Use great_fit_pitch value
- "Challenging project", "Tell us about a project" → Use challenging_project value

STEP 5 - HANDLE SPECIAL FIELD TYPES:
- DROPDOWNS: Click to open the dropdown, then click the matching option
- RADIO BUTTONS: Click the appropriate option
- CHECKBOXES: Click to check/uncheck as needed
- FILE UPLOAD: Click the upload button/area and select the resume file
- LOCATION/CITY AUTOCOMPLETE (CRITICAL - often fails):
  1. Click on the Location input field
  2. Type the city name (e.g., "Buffalo" or "New York")
  3. WAIT 1-2 seconds for autocomplete suggestions to appear
  4. Look for a dropdown with matching cities
  5. Click on the matching city option from the dropdown
  6. Verify the field now shows the selected location
  If no dropdown appears, try typing more characters or a different city format

STEP 6 - FORM VALIDATION (MANDATORY):
Scroll through the ENTIRE form from top to bottom and validate EACH of these:

VALIDATION CHECKLIST:
☐ Name field - Is it filled with the applicant's name?
☐ Email field - Is it filled with a valid email?
☐ Phone field - Is it filled with a phone number?
☐ Location field - Does it show a selected city (not empty)?
☐ Resume - Is the file uploaded (shows filename)?
☐ LinkedIn/GitHub/Portfolio - Are optional but fill if present
☐ Work Authorization - Is a selection made?
☐ Required questions - Are all required text boxes filled?

HOW TO CHECK:
- Look at each field visually - does it have a value?
- Fields with * or "required" MUST have values
- Empty fields will appear blank or show placeholder text like "Enter..."

IF ANY REQUIRED FIELD IS EMPTY:
→ Go back to that field and fill it
→ For Location: follow the autocomplete steps (type city, wait, click suggestion)
→ Re-run this validation checklist

STEP 7 - EXTRACT FORM STATE (FINAL STEP):
⚠️ DO NOT SUBMIT - INSTEAD, extract and report the form state ⚠️

For each field you filled, extract:
- field_id: A **UNIQUE** identifier for the field. Prioritize `id` attribute, then `name` attribute, then a unique CSS selector (e.g., `input[type='text']:nth-of-type(1)`). **CRITICAL: No two fields can have the same field_id.**
- field_type: text, email, select, checkbox, radio, file, textarea
- label: The field's visible label
- value: The value you entered
- required: Whether the field was required

Return your result as a JSON object with this structure:
{{
  "status": "prefilled",
  "page_url": "{job_link}",
  "fields": [
    {{"field_id": "first_name", "field_type": "text", "label": "First Name", "value": "John", "confidence": 0.95, "required": true}},
    {{"field_id": "email", "field_type": "email", "label": "Email", "value": "john@example.com", "confidence": 0.95, "required": true}},
    ...
  ],
  "validation_passed": true,
  "notes": "Any issues or observations about the form"
}}

IMPORTANT: Return the JSON directly in your final response text. 
⚠️ DO NOT create a file, artifact, or attachment. 
⚠️ DO NOT say "see attached file". 
⚠️ The JSON must be in the text response itself.

===== IMPORTANT GUIDELINES =====
- Fill ALL required fields - don't leave them empty
- LOCATION is usually a dropdown that requires clicking to open and selecting a city
- For optional fields with no matching data, leave blank or enter "N/A"
- For "How did you hear about us?" type questions, select "Job Board", "Other", or similar
- If a field seems unresponsive, try clicking it again before typing
- Take your time - accuracy is more important than speed
- NEVER click Submit, Apply, Send Application, or any similar button
- The user will review the form and submit it manually

===== REMEMBER =====
Your task is complete when:
1. All fields are filled correctly
2. You have extracted the form state
3. You have NOT clicked submit

DO NOT SUBMIT THE APPLICATION.
"""

# Legacy alias for backwards compatibility - will be removed in future version
APPLY_JOB_TASK_TEMPLATE = PREFILL_JOB_TASK_TEMPLATE

RESUME_OPTIMIZER_PROMPT_TEMPLATE = """
You are an expert ATS optimizer.
Analyze the Job Description and extract the most important technical keywords, skills, and tools mentioned.

Job Description:
{job_description}

Return a JSON object with a single key:
- skills_list: A list of the top 10-15 most relevant keywords/skills found in the description.

Do not manufacture skills that are completely unrelated to software engineering, but prioritize matching the JD hard skills.
"""
