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

APPLY_JOB_TASK_TEMPLATE = """
You are a job application assistant. Your task is to fill out a job application form accurately and completely.

TASK: Apply to the job posting at {job_link}

===== APPLICANT INFORMATION =====
{user_details}

===== RESUME FILE =====
Upload this file when asked for resume: {abs_resume_path}

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

STEP 6 - PRE-SUBMIT VALIDATION (MANDATORY):
⚠️ STOP! DO NOT CLICK SUBMIT UNTIL YOU COMPLETE THIS CHECKLIST ⚠️

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
→ DO NOT submit yet
→ Go back to that field and fill it
→ For Location: follow the autocomplete steps (type city, wait, click suggestion)
→ Re-run this validation checklist

ONLY PROCEED TO SUBMIT WHEN ALL REQUIRED FIELDS ARE FILLED.

STEP 7 - SUBMIT:
Click the "Submit", "Submit Application", or similar button.

STEP 8 - ERROR RECOVERY (CRITICAL):
After clicking submit, WAIT 2 seconds and check the page:

IF YOU SEE A SUCCESS/CONFIRMATION MESSAGE:
→ Report success and you're done!

IF YOU SEE ERROR MESSAGES (red text, highlighted fields, "required", etc.):
→ DO NOT report success yet. Follow this error recovery process:

1. IDENTIFY THE ERROR:
   - Read the error message carefully
   - Identify which field(s) are failing
   
2. TRY DIFFERENT STRATEGIES TO FIX:

   For LOCATION/CITY errors:
   - Strategy A: Click the field, type "New York", wait 3 seconds, click first suggestion
   - Strategy B: Click the field, type just "New", wait 3 seconds, look for dropdown
   - Strategy C: Try "San Francisco" or "Los Angeles" instead
   
   For TEXT FIELD errors:
   - Strategy A: Click the field, select all (Ctrl+A), delete, retype the value
   - Strategy B: Scroll the field into view first, then click and type
   - Strategy C: Tab to the field instead of clicking
   
   For DROPDOWN errors:
   - Strategy A: Click to open, wait 1 second, click first available option
   - Strategy B: Type to filter, then click matching option
   
   For CHECKBOX/RADIO errors:
   - Strategy A: Scroll to make it visible, then click
   - Strategy B: Click the label text instead of the checkbox itself

3. AFTER FIXING:
   - Verify the field now shows a value
   - Click Submit again
   - Repeat this process up to 3 times
   
4. FINAL REPORT:
   - If successful after retries → Report success
   - If still failing after 3 attempts → Report failure with the specific error

===== IMPORTANT GUIDELINES =====
- Fill ALL required fields - don't leave them empty
- LOCATION is usually a dropdown that requires clicking to open and selecting a city
- For optional fields with no matching data, leave blank or enter "N/A"
- For "How did you hear about us?" type questions, select "Job Board", "Other", or similar
- If a field seems unresponsive, try clicking it again before typing
- Take your time - accuracy is more important than speed
- If you see an error after submit, FIX IT and try again
- Only report success if you see a confirmation message with no errors
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
