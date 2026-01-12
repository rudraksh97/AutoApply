"""
Centralized repository for AI/LLM prompts used across the application.
"""

# =============================================================================
# DETERMINISTIC FORM EXTRACTION ENGINE
# =============================================================================
# You are a deterministic, browser-native form understanding engine.
# Your job is to extract form structure (labels + xpaths) WITHOUT filling.
# A separate LLM step will generate answers based on user profile.
#
# PRIORITY: Correctness > Speed > Reliability > Cleverness
# =============================================================================

FORM_EXTRACTION_CONTEXT = """
You are a DETERMINISTIC form EXTRACTION engine. DO NOT FILL ANY FIELDS.
Your only job is to discover inputs and extract their labels and XPaths.

═══════════════════════════════════════════════════════════════════════════════
GLOBAL RULES (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════════════════════
• DO NOT FILL ANY FIELDS - extraction only
• DO NOT type any values into inputs
• DO NOT click on form fields (except to dismiss popups)
• DO NOT submit the form
• ONLY extract labels and XPaths

═══════════════════════════════════════════════════════════════════════════════
STEP 1: DISCOVER RELEVANT INPUTS
═══════════════════════════════════════════════════════════════════════════════
Scan the DOM once and collect:
  ✓ <input> elements
  ✓ <textarea> elements
  ✓ <select> elements

EXCLUDE from collection:
  ✗ type="hidden"
  ✗ disabled elements
  ✗ elements not visible (offsetParent === null)

═══════════════════════════════════════════════════════════════════════════════
STEP 2: RESOLVE LABEL (DETERMINISTIC PRIORITY ORDER)
═══════════════════════════════════════════════════════════════════════════════
For each input, resolve its label in THIS EXACT ORDER. STOP at first success:

  1. <label for="input.id">           → Explicit label association
  2. Wrapped <label> ancestor         → Label wrapping the input
  3. aria-label attribute             → Accessibility label
  4. aria-labelledby reference        → Referenced label element
  5. placeholder attribute            → Fallback hint text
  6. <fieldset><legend>               → Group label
  7. Immediate preceding <label>      → DOM-adjacent sibling only

LABEL RESOLUTION RULES:
  • Use textContent, NEVER innerText
  • Trim all whitespace
  • Do NOT concatenate unrelated text
  • If no label found → mark label as null

═══════════════════════════════════════════════════════════════════════════════
STEP 3: EXTRACT XPATH FOR EACH INPUT
═══════════════════════════════════════════════════════════════════════════════
For each input element, extract its FULL XPATH path.

Example XPaths:
  • //*[@id="email"]
  • //input[@name="first_name"]
  • //form//input[@type="text"][1]
  • //textarea[@placeholder="Tell us about yourself"]

RULES:
  • Use rooted XPath (starting with //)
  • Prefer @id or @name attributes when available for stability
  • Each xpath MUST uniquely identify ONE element
  • For <select>, also extract all <option> values

═══════════════════════════════════════════════════════════════════════════════
STEP 4: EXTRACT SELECT OPTIONS
═══════════════════════════════════════════════════════════════════════════════
For <select> elements, extract all available options:
  • Get text content of each <option>
  • Include in the "options" array

═══════════════════════════════════════════════════════════════════════════════
CRITICAL REMINDERS
═══════════════════════════════════════════════════════════════════════════════
⚠️  DO NOT FILL ANY FIELDS
⚠️  DO NOT TYPE INTO ANY INPUTS
⚠️  DO NOT SUBMIT THE FORM
⚠️  ONLY EXTRACT STRUCTURE (labels, xpaths, options)
⚠️  ALWAYS RETURN JSON OUTPUT
"""

# Legacy alias - keeping for backwards compatibility
FORM_FILLING_CONTEXT = FORM_EXTRACTION_CONTEXT

SCRAPE_JOB_TASK_TEMPLATE = """
Go to {job_link}.
Extract the full job description, responsibilities, and requirements.
Return the result as a structured string.
"""

EXTRACT_FORM_TASK_TEMPLATE = """
You are a DETERMINISTIC form EXTRACTION engine. DO NOT FILL ANY FIELDS.

═══════════════════════════════════════════════════════════════════════════════
TASK: Extract form structure from {job_link}
═══════════════════════════════════════════════════════════════════════════════

⚠️  CRITICAL: DO NOT FILL ANY FIELDS  ⚠️
⚠️  DO NOT TYPE INTO ANY INPUTS  ⚠️
⚠️  DO NOT SUBMIT THE FORM  ⚠️
⚠️  EXTRACTION ONLY  ⚠️

═══════════════════════════════════════════════════════════════════════════════
EXECUTION STEPS
═══════════════════════════════════════════════════════════════════════════════

STEP 1 — NAVIGATE
  • Go to {job_link}
  • Wait for page to fully load
  • Dismiss any cookie/popup dialogs (click X or "Accept")
  • DO NOT interact with form fields

STEP 2 — DISCOVER ALL FORM INPUTS
  Scan DOM and collect ALL:
    ✓ <input> elements (visible, not hidden, not disabled)
    ✓ <textarea> elements (visible)
    ✓ <select> elements (visible)

  EXCLUDE:
    ✗ type="hidden"
    ✗ disabled elements
    ✗ submit/button elements

STEP 3 — FOR EACH INPUT, EXTRACT:

  3a. EXTRACT XPATH:
      Generate a unique XPath that identifies this element.
      
      Priority order:
        1. //*[@id="element_id"] (if has id)
        2. //input[@name="field_name"] (if has name)
        3. //tagname[@placeholder="..."] (if has placeholder)
        4. Full path: //form//div[2]//input[1]
      
      RULES:
        • XPath MUST uniquely identify ONE element
        • Prefer @id or @name for stability
        • Test mentally: would this find exactly one element?

  3b. RESOLVE LABEL (priority order, stop at first success):
      1. <label for="input.id"> → use label's textContent
      2. Wrapped <label> ancestor → use ancestor's textContent
      3. aria-label attribute
      4. aria-labelledby → find referenced element's text
      5. placeholder attribute
      6. <fieldset><legend> → use legend text
      7. Preceding <label> sibling in DOM

  3c. DETERMINE FIELD TYPE:
      • text, email, phone, tel → "text" or "email" or "phone"
      • password → "password"
      • checkbox → "checkbox"
      • radio → "radio"
      • file → "file"
      • <textarea> → "textarea"
      • <select> → "select"

  3d. FOR <select> ELEMENTS — EXTRACT OPTIONS:
      Get ALL <option> elements and their text values.
      Return as "options" array.

  3e. DETERMINE IF REQUIRED:
      • Has "required" attribute → true
      • Label contains "*" → true
      • aria-required="true" → true
      • Otherwise → false

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Return JSON with this EXACT structure:

{{
  "status": "extracted",
  "page_url": "{job_link}",
  "fields": [
    {{
      "xpath": "//*[@id='email']",
      "field_type": "email",
      "label": "Email Address",
      "required": true,
      "options": null
    }},
    {{
      "xpath": "//select[@name='country']",
      "field_type": "select",
      "label": "Country",
      "required": true,
      "options": ["United States", "Canada", "United Kingdom", "Other"]
    }},
    {{
      "xpath": "//textarea[@placeholder='Tell us about yourself']",
      "field_type": "textarea",
      "label": "Why are you interested in this role?",
      "required": false,
      "options": null
    }}
  ],
  "total_fields": <number of fields found>,
  "notes": "<any observations about the form>"
}}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════
⚠️  DO NOT include "value" in the output - we only extract structure
⚠️  DO NOT fill any fields
⚠️  DO NOT type into any inputs
⚠️  DO NOT click on form fields (only dismiss popups)
⚠️  ALWAYS return JSON - never just text
⚠️  Extract ALL visible form fields, not just some

If you cannot extract a field's label, set label to null but still include the field.
If you cannot determine xpath, use the best approximation with a note.

═══════════════════════════════════════════════════════════════════════════════
REMEMBER
═══════════════════════════════════════════════════════════════════════════════
✓ Navigate to page
✓ Discover all form inputs
✓ Extract xpath, label, field_type, required, options for each
✓ Return JSON with all fields
✗ DO NOT fill any values
✗ DO NOT type into inputs
✗ DO NOT submit the form
"""

# Legacy aliases for backwards compatibility
PREFILL_JOB_TASK_TEMPLATE = EXTRACT_FORM_TASK_TEMPLATE
APPLY_JOB_TASK_TEMPLATE = EXTRACT_FORM_TASK_TEMPLATE


# =============================================================================
# LLM ANSWER GENERATION PROMPT
# =============================================================================
# After form extraction, this prompt generates answers based on user profile

GENERATE_FORM_ANSWERS_PROMPT = """
You are a job application assistant. Generate appropriate answers for form fields based on the applicant's profile.

═══════════════════════════════════════════════════════════════════════════════
JOB DETAILS
═══════════════════════════════════════════════════════════════════════════════
{job_description}

═══════════════════════════════════════════════════════════════════════════════
APPLICANT PROFILE
═══════════════════════════════════════════════════════════════════════════════
{user_profile}

═══════════════════════════════════════════════════════════════════════════════
FORM FIELDS TO FILL
═══════════════════════════════════════════════════════════════════════════════
{form_fields}

═══════════════════════════════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

For each field, generate an appropriate value based on the applicant's profile.

FIELD MAPPING RULES:
┌──────────────────────────────┬────────────────────────────────────────────┐
│ Label Contains               │ Use This Value                             │
├──────────────────────────────┼────────────────────────────────────────────┤
│ first name, given name       │ Profile first_name                         │
│ last name, surname           │ Profile last_name                          │
│ full name, name              │ Profile first_name + " " + last_name       │
│ email                        │ Profile email                              │
│ phone, mobile, cell, tel     │ Profile phone                              │
│ location, city, address      │ Profile location                           │
│ linkedin                     │ Profile linkedin URL                       │
│ github                       │ Profile github URL                         │
│ portfolio, website           │ Profile portfolio URL                      │
│ gender                       │ Profile gender                             │
│ race, ethnicity              │ Profile race                               │
│ veteran                      │ Profile veteran_status                     │
│ disability                   │ Profile disability_status                  │
│ work authorization           │ "Yes" if authorized, else "No"             │
│ sponsorship, visa            │ "Yes" if requires sponsorship, else "No"   │
│ relocate, relocation         │ "Yes"                                      │
│ how did you hear             │ "Job Board" or "LinkedIn" or "Other"       │
│ salary, compensation         │ null (leave for user)                      │
│ start date, availability     │ null (leave for user)                      │
└──────────────────────────────┴────────────────────────────────────────────┘

FOR OPEN-ENDED QUESTIONS (why interested, tell us about yourself, etc.):
  • Write a concise, professional response (2-4 sentences)
  • Reference the specific company/role from job details
  • Highlight relevant experience from profile
  • Be genuine and specific, not generic

FOR <select> FIELDS:
  • Choose from the available "options" array
  • Match semantically (e.g., "Yes" matches "Yes, I am authorized")
  • Return the exact option text that should be selected

FOR CHECKBOX/RADIO FIELDS:
  • Return "true" or "false" for checkboxes
  • Return the option value for radio buttons

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Return a JSON array with values for each field:

[
  {{
    "xpath": "<xpath from input>",
    "value": "<generated value>",
    "confidence": <0.0-1.0>,
    "skip": <true if should be left for user>,
    "skip_reason": "<reason if skipped>"
  }}
]

CONFIDENCE LEVELS:
  • 1.0: Direct profile match (name, email, phone)
  • 0.8: Clear semantic match (work auth → Yes/No)
  • 0.6: Generated response (why interested, cover letter)
  • 0.0: Cannot determine / skip for user

SET skip=true FOR:
  • Salary/compensation questions
  • Start date/availability
  • Legal agreements/consent checkboxes
  • Questions requiring information not in profile
  • Ambiguous fields

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT
═══════════════════════════════════════════════════════════════════════════════
• Return ONLY the JSON array
• Include ALL fields from input (even if skipped)
• Use null for value if skip=true
• Match xpath exactly from input
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
