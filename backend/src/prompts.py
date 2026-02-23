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
  ✓ <input> elements (including type="checkbox" and type="radio")
  ✓ <textarea> elements
  ✓ <select> elements
  ✓ Custom binary choice elements (Yes/No buttons, styled radio groups)
    - Elements with role="radio" or role="checkbox"
    - Elements inside [role="radiogroup"]
    - Button groups with "Yes"/"No" or similar binary text

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
  5. <fieldset><legend>               → Group label
  6. Immediate preceding <label>      → DOM-adjacent sibling in DOM
  7. Nearby text (within same container) → Text immediately before/above input
  8. placeholder attribute            → ONLY if descriptive (see rules below)

LABEL RESOLUTION RULES:
  • Use textContent, NEVER innerText
  • Trim all whitespace
  • Do NOT concatenate unrelated text
  • If no label found → mark label as null

PLACEHOLDER VALIDATION (for step 8):
  ⚠️ IGNORE generic/non-descriptive placeholders. Skip if placeholder contains:
    - "start typing", "type here", "enter", "input", "search"
    - "select", "choose", "pick", "click"
    - Single words like "text", "value", "answer"
  ✓ ONLY use placeholder if it's actually descriptive, like:
    - "Email address", "Phone number", "Company name"
    - "Describe your experience", "Why are you interested?"

═══════════════════════════════════════════════════════════════════════════════
STEP 3: EXTRACT XPATH FOR EACH INPUT
═══════════════════════════════════════════════════════════════════════════════
For each input element, extract its FULL XPATH path.

⚠️ CRITICAL: Each xpath MUST uniquely identify ONE element on the page!

XPATH PRIORITY ORDER (use first available):
  1. @id attribute: //*[@id="email"]
  2. @name attribute: //input[@name="first_name"]
  3. @aria-labelledby: //*[@aria-labelledby="question_123"]
  4. Unique @data-* attribute: //*[@data-testid="work-auth-radio"]
  5. Ancestor context + position: //div[@class="question"][1]//button[text()='Yes']
  6. Positional index: (//button[text()='Yes'])[1]

RULES:
  • Use rooted XPath (starting with //)
  • Prefer @id or @name attributes when available for stability
  • Each xpath MUST uniquely identify ONE element
  • For <select>, also extract all <option> values

⚠️ MULTIPLE SIMILAR ELEMENTS (e.g., multiple Yes/No button groups):
  When multiple elements match the same pattern, you MUST differentiate them:
  
  BAD:  //button[text()='Yes']  ← Matches ALL Yes buttons on page!
  
  GOOD options:
    • Use positional index: (//button[text()='Yes'])[1], (//button[text()='Yes'])[2]
    • Use parent/ancestor context: //div[contains(.,'work authorization')]//button[text()='Yes']
    • Use aria-labelledby if available: //*[@aria-labelledby='question_work_auth']//button[text()='Yes']
    • Use nearby label text: //label[contains(.,'eligible to work')]/following-sibling::*//button[text()='Yes']
  
  TEST: Ask yourself "Would this xpath match more than one element?" If yes, make it more specific!

═══════════════════════════════════════════════════════════════════════════════
STEP 4: EXTRACT OPTIONS FOR SELECT AND RADIO GROUPS
═══════════════════════════════════════════════════════════════════════════════
For <select> elements:
  • Get text content of each <option>
  • Include in the "options" array

For RADIO BUTTON GROUPS (input type="radio"):
  • Find all radio inputs with the SAME name attribute (they form a group)
  • Extract the label text for EACH radio button in the group
  • Include all labels in the "options" array
  • Use ONE entry for the entire group, not one per radio button
  • The xpath should point to the FIRST radio button in the group

Example: Radio group with name="work_authorization"
  - Radio 1: label="Yes, I am authorized"
  - Radio 2: label="No, I require sponsorship"
  → options: ["Yes, I am authorized", "No, I require sponsorship"]

For CHECKBOX inputs:
  • Single checkboxes do NOT need options (they're true/false)
  • Only extract the label

═══════════════════════════════════════════════════════════════════════════════
STEP 5: IDENTIFY CUSTOM BINARY CHOICE ELEMENTS (ARIA RADIO GROUPS)
═══════════════════════════════════════════════════════════════════════════════
Modern forms often use STYLED ELEMENTS instead of native radio/checkbox inputs.
These are usually wrapped in a container with role="radiogroup".

⚠️ CRITICAL: Extract ONE entry per group, NOT one per option!
⚠️ CRITICAL: Each xpath MUST be UNIQUE - no two fields can have the same xpath!

DETECTION PATTERNS:
  ✓ <fieldset role="radiogroup"> or <div role="radiogroup">
  ✓ Container with aria-labelledby pointing to question text
  ✓ Children with role="radio" or data-ui="option"
  ✓ Elements with aria-checked attribute

EXTRACTION RULES for role="radiogroup" containers:
  1. LABEL: Use aria-labelledby to find the question text!
     - Get the aria-labelledby ID from the radiogroup
     - Find the element with that ID and use its textContent as label
     - IGNORE any text from SVG elements or aria-hidden="true" elements
  
  2. XPATH: Point to the radiogroup container - MUST BE UNIQUE!
     
     ⚠️ When multiple Yes/No groups exist, use one of these strategies:
     
     BEST: Use aria-labelledby (if available):
       //*[@role='radiogroup' and @aria-labelledby='work_auth_label']
       //*[@role='radiogroup' and @aria-labelledby='sponsorship_label']
     
     GOOD: Use positional index to differentiate:
       (//*[@role='radiogroup'])[1]  ← First Yes/No group
       (//*[@role='radiogroup'])[2]  ← Second Yes/No group
     
     GOOD: Use ancestor/parent context:
       //div[contains(.,'eligible to work')]//*[@role='radiogroup']
       //div[contains(.,'visa sponsorship')]//*[@role='radiogroup']
     
     BAD: Generic xpath that matches multiple groups:
       //*[@role='radiogroup']  ← DON'T USE if multiple exist!
       //button[text()='Yes']   ← DON'T USE - matches all Yes buttons!
  
  3. OPTIONS: Extract text from each child with role="radio"
     - Look for text in <span> or direct textContent
     - IGNORE SVG icons and aria-hidden elements
     - Return as array: ["Yes", "No"] or ["Option 1", "Option 2"]
  
  4. field_type: "radio"

Example: TWO Yes/No questions on same page:
  Question 1: "Are you eligible to work in the US?"
  Question 2: "Do you require visa sponsorship?"
  
  Correct xpaths (each is unique):
    → xpath: "(//*[@role='radiogroup'])[1]" or "//*[@aria-labelledby='q1_label']"
    → xpath: "(//*[@role='radiogroup'])[2]" or "//*[@aria-labelledby='q2_label']"
  
  ❌ WRONG: Both fields having xpath "//button[text()='Yes']"

❌ WRONG: Creating separate entries for YES and NO
❌ WRONG: Using "SVGs not supported..." as label (that's fallback SVG text)
❌ WRONG: Two fields with identical xpaths
✓ RIGHT: ONE entry per group with UNIQUE xpath and options array

═══════════════════════════════════════════════════════════════════════════════
CRITICAL REMINDERS
═══════════════════════════════════════════════════════════════════════════════
⚠️  DO NOT FILL ANY FIELDS
⚠️  DO NOT TYPE INTO ANY INPUTS
⚠️  DO NOT SUBMIT THE FORM
⚠️  ONLY EXTRACT STRUCTURE (labels, xpaths, options)
⚠️  ALWAYS RETURN JSON OUTPUT
"""


SCRAPE_JOB_TASK_TEMPLATE = """
TASK: Extract job details and find the apply link from {job_link}

═══════════════════════════════════════════════════════════════════════════════
🚨 CRITICAL: RETURN ONLY VALID JSON IN THE DONE ACTION!
═══════════════════════════════════════════════════════════════════════════════
• Your done action MUST contain ONLY a valid JSON object
• DO NOT include explanatory text like "I'll extract" or "Here's the data"
• Start directly with the JSON object - no conversational preamble
• The system expects pure JSON, not text with JSON embedded

═══════════════════════════════════════════════════════════════════════════════
⚠️  CRITICAL OUTPUT RULES - READ FIRST!
═══════════════════════════════════════════════════════════════════════════════
• DO NOT use write_file action - return all data directly in the done action
• DO NOT create file attachments
• ALL fields in the JSON must be populated with actual values
• Empty strings ("") are NOT acceptable for job_description and job_title

═══════════════════════════════════════════════════════════════════════════════
STEP 1: Navigate and wait
═══════════════════════════════════════════════════════════════════════════════
1. Go to {job_link}
2. Wait 15 seconds for page load
3. Dismiss any cookie banners or popups

═══════════════════════════════════════════════════════════════════════════════
STEP 2: Extract job details FIRST (before any clicks!)
═══════════════════════════════════════════════════════════════════════════════
Read and memorize:
• job_title: The main heading (usually h1)
• location: City/state/country or "Remote"
• job_description: The FULL job posting text including:
  - Role overview / About the role
  - Responsibilities
  - Requirements / Qualifications
  - Benefits (if listed)
  
⚠️  Store this information NOW - you will need it for the final JSON.

═══════════════════════════════════════════════════════════════════════════════
STEP 3: Determine the apply_link
═══════════════════════════════════════════════════════════════════════════════
Look at the current page state:

CASE A - Application form is ALREADY visible:
  → You can see form fields (name, email, resume upload) without clicking
  → apply_link = current browser URL
  → Go to Step 4

CASE B - There is an Apply button (no form visible yet):
  → Find button with text like "Apply", "Apply Now", "Apply for this job"
  → CLICK the button
  → Wait 15 seconds
  → Check what happened:
  
    If URL changed → apply_link = the NEW URL
    If form/modal appeared but URL unchanged → apply_link = current URL
    If page redirected externally → apply_link = the new external URL
  
  → Go to Step 4

CASE C - Cannot find Apply button or form:
  → apply_link = {job_link} (use original URL as fallback)
  → Note this in your response

═══════════════════════════════════════════════════════════════════════════════
STEP 4: Return JSON directly in done action
═══════════════════════════════════════════════════════════════════════════════
Call done with this EXACT JSON structure. ALL fields must have values:

{{
  "job_description": "< PASTE THE FULL JOB DESCRIPTION TEXT HERE - must be 100+ words >",
  "apply_link": "< URL where the application form is - from Step 3 >",
  "job_title": "< job title >",
  "location": "< location or Remote >",
  "notes": "< what you observed: was form visible? did you click Apply? did URL change? >"
}}

═══════════════════════════════════════════════════════════════════════════════
❌ FORBIDDEN ACTIONS
═══════════════════════════════════════════════════════════════════════════════
• DO NOT use write_file - return data in done action only
• DO NOT return empty strings for required fields
• DO NOT extract form input fields - that's a separate task
• DO NOT return the JSON as a file attachment

✅ REQUIRED
═══════════════════════════════════════════════════════════════════════════════
• job_description MUST contain the actual job posting text (100+ words)
• apply_link MUST be a valid URL
• job_title MUST be filled in
• Return ALL data directly in the done action JSON
"""

EXTRACT_FORM_TASK_TEMPLATE = """
🚀 FIRST ACTION: Navigate to {job_link} immediately. Do not wait - navigate now!

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

STEP 1 — NAVIGATE (DO THIS FIRST!)
  • Navigate to {job_link} using the navigate action
  • Wait 15 seconds for page to fully load
  • Dismiss any cookie/popup dialogs (click X or "Accept")
  • DO NOT interact with form fields

STEP 2 — DISCOVER ALL FORM INPUTS
  Scan DOM and collect ALL:
    ✓ <input> elements (visible, not hidden, not disabled)
    ✓ <textarea> elements (visible)
    ✓ <select> elements (visible)
    ✓ Custom binary choice elements:
      - Elements with role="radio" or role="checkbox"
      - Container with role="radiogroup"
      - Button groups with "Yes"/"No" text

  EXCLUDE:
    ✗ type="hidden"
    ✗ disabled elements
    ✗ submit/button elements (except Yes/No choice buttons)

STEP 3 — FOR EACH INPUT, EXTRACT:

  3a. EXTRACT XPATH:
      Generate a UNIQUE XPath that identifies ONLY this element.
      
      ⚠️ CRITICAL: No two fields can have the same xpath!
      
      Priority order:
        1. //*[@id="element_id"] (if has id)
        2. //input[@name="field_name"] (if has name)
        3. //*[@aria-labelledby="label_id"] (for radio groups)
        4. //tagname[@placeholder="..."] (if has placeholder)
        5. Positional index: (//button[text()='Yes'])[1]
        6. Parent context: //div[contains(.,'question text')]//button[text()='Yes']
      
      RULES:
        • XPath MUST uniquely identify ONE element
        • Prefer @id or @name for stability
        • Test mentally: would this find exactly one element?
      
      ⚠️ MULTIPLE Yes/No GROUPS:
        When page has multiple Yes/No button pairs, you MUST differentiate:
        
        ❌ BAD:  //button[text()='Yes']  ← Matches ALL Yes buttons!
        
        ✓ GOOD: Use positional index:
          (//button[text()='Yes'])[1]  ← First Yes/No question
          (//button[text()='Yes'])[2]  ← Second Yes/No question
        
        ✓ GOOD: Use parent/ancestor context with question text:
          //div[contains(.,'eligible to work')]//button[text()='Yes']
          //div[contains(.,'visa sponsorship')]//button[text()='Yes']

  3b. RESOLVE LABEL (priority order, stop at first success):
      1. <label for="input.id"> → use label's textContent
      2. Wrapped <label> ancestor → use ancestor's textContent
      3. aria-label attribute
      4. aria-labelledby → find referenced element's text
         ⚠️ IMPORTANT for role="radiogroup": ALWAYS check aria-labelledby!
         The question text is usually in a separate element referenced by ID.
      5. <fieldset><legend> → use legend text
      6. Preceding <label> sibling in DOM
      7. Nearby text (within same container) → text immediately before/above input
      8. placeholder attribute → ONLY if descriptive (NOT generic like "start typing")
      
      ⚠️ PLACEHOLDER RULE: Skip generic placeholders like "start typing", 
         "type here", "enter value", "select option". Only use placeholder 
         if it describes the field (e.g., "Email address", "Phone number").
      
      ⚠️ SVG/ICON RULE: IGNORE text from elements with aria-hidden="true".
         This includes SVG icons - they often have fallback text like 
         "SVGs not supported" which is NOT the field label.

  3c. DETERMINE FIELD TYPE:
      • text, email, phone, tel → "text" or "email" or "phone"
      • password → "password"
      • checkbox → "checkbox" (single true/false toggle)
      • radio → "radio" (multiple choice, including Yes/No)
      • file → "file"
      • <textarea> → "textarea"
      • <select> → "select"
      • Custom Yes/No buttons → "radio" (with options: ["Yes", "No"])

  3d. FOR <select> AND RADIO GROUPS — EXTRACT OPTIONS:
      
      For <select>:
        Get ALL <option> elements and their text values.
      
      For RADIO BUTTON GROUPS (input type="radio"):
        • Find all radio inputs with the SAME name attribute
        • Extract the label text for EACH radio in the group
        • Return ONE field for the whole group (not one per radio)
        • xpath should point to the FIRST radio button
        
        Example: name="authorized_to_work"
          Radio 1 label: "Yes" → Radio 2 label: "No"
          → options: ["Yes", "No"]
      
      Return as "options" array.

  3e. DETERMINE IF REQUIRED:
      • Has "required" attribute → true
      • Label contains "*" → true
      • aria-required="true" → true
      • Otherwise → false

  3f. FOR CUSTOM RADIO GROUPS (role="radiogroup" or Yes/No buttons):
      Modern forms use styled elements instead of native radio inputs.
      These are wrapped in containers with role="radiogroup" or are button pairs.
      
      ⚠️ CRITICAL: Create ONE entry per group, NOT one per option!
      ⚠️ CRITICAL: Each xpath MUST be UNIQUE across all fields!
      
      DETECT by:
        • <fieldset role="radiogroup"> or <div role="radiogroup">
        • Container with aria-labelledby attribute
        • Children with role="radio" or data-ui="option"
        • Elements with aria-checked attribute
        • Button pairs with Yes/No text
      
      EXTRACT as:
        • field_type: "radio"
        • xpath: Point to the radiogroup CONTAINER - MUST BE UNIQUE!
        • label: MUST use aria-labelledby to find the question text!
        • options: Extract text from EACH child with role="radio"
      
      ⚠️ MULTIPLE Yes/No GROUPS ON SAME PAGE:
        When multiple radio groups exist, each MUST have a UNIQUE xpath:
        
        ✓ BEST - Use aria-labelledby (if available):
          //*[@role='radiogroup'][@aria-labelledby='q1_label']
          //*[@role='radiogroup'][@aria-labelledby='q2_label']
        
        ✓ GOOD - Use positional index:
          (//*[@role='radiogroup'])[1]
          (//*[@role='radiogroup'])[2]
        
        ✓ GOOD - Use parent context with question text:
          //div[contains(.,'eligible to work')]//*[@role='radiogroup']
          //div[contains(.,'visa sponsorship')]//*[@role='radiogroup']
        
        ❌ BAD - Same xpath for different questions:
          //button[text()='Yes']  ← Matches ALL Yes buttons!
      
      Example with TWO questions:
        Q1: "Are you eligible to work?" → xpath: "(//*[@role='radiogroup'])[1]"
        Q2: "Need visa sponsorship?"    → xpath: "(//*[@role='radiogroup'])[2]"
      
      ❌ WRONG: Creating separate entries for each option
      ❌ WRONG: Using SVG fallback text as label
      ❌ WRONG: Two fields with the same xpath

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
    }},
    {{
      "xpath": "//input[@name='work_authorization'][1]",
      "field_type": "radio",
      "label": "Are you authorized to work in the US?",
      "required": true,
      "options": ["Yes", "No"]
    }},
    {{
      "xpath": "//input[@type='checkbox'][@name='agree_terms']",
      "field_type": "checkbox",
      "label": "I agree to the terms and conditions",
      "required": true,
      "options": null
    }},
    {{
      "xpath": "//*[@role='radiogroup']",
      "field_type": "radio",
      "label": "Do you require visa sponsorship?",
      "required": true,
      "options": ["Yes", "No"]
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
⚠️  NEVER use generic placeholders as labels (e.g., "start typing", "enter value")

LABEL QUALITY CHECK:
  Before using a placeholder as label, ask: "Does this text describe WHAT the field is for?"
  ✗ BAD labels: "start typing", "type here", "enter", "select", "search..."
  ✓ GOOD labels: "Email address", "First name", "Years of experience"
  If no descriptive label found, set label to null - don't use generic placeholder text.

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


# =============================================================================
# LLM ANSWER GENERATION PROMPT
# =============================================================================

GENERATE_FORM_ANSWERS_PROMPT = """
You are a job application assistant. Generate answers for form fields using the applicant's profile.
Fill as many fields as possible using profile data, reasonable assumptions, or generated responses.

---
JOB DETAILS:
{job_description}

---
APPLICANT PROFILE:
{user_profile}

---
FORM FIELDS TO FILL:
{form_fields}

---
FIELD MAPPING RULES

1. PROFILE FIELDS (direct match, confidence=1.0):
   - first name, given name, fname -> profile first_name
   - last name, surname, family name -> profile last_name  
   - full name, your name -> first_name + " " + last_name
   - email -> profile email
   - phone, mobile, cell, tel -> profile phone
   - location, city, address -> profile location
   - linkedin -> profile linkedin URL
   - github -> profile github URL
   - portfolio, website -> profile portfolio URL
   - country -> profile country or "United States"
   - state, province -> extract from profile location
   - zip, postal code -> extract from profile location

2. WORK AUTHORIZATION (confidence=0.8):
   - "authorized to work", "work authorization" -> "Yes" if profile authorized, else "No"
   - "sponsorship", "visa", "require sponsorship" -> "Yes" if needs sponsorship, else "No"

3. DEMOGRAPHICS / EEO (confidence=0.8):
   - gender, sex -> profile gender
   - race, ethnicity -> profile race
   - veteran status -> profile veteran_status
   - disability -> profile disability_status
   - Hispanic/Latino questions -> "Yes" ONLY if profile race contains "Hispanic" or "Latino", otherwise "No"
   
   Match profile values to the closest available option.
   Only use "Prefer not to say" if the profile explicitly states it.

4. CONTEXTUAL DEFAULTS (confidence=0.7):
   - relocate, willing to relocate -> "Yes"
   - remote, willing to work remote -> "Yes"
   - travel, willing to travel -> "Yes" or "Up to 25%"
   - how did you hear, source -> "Job Board" or "LinkedIn"
   - years of experience -> calculate from profile experience dates
   - current company, employer -> most recent from profile
   - current title, role -> most recent from profile
   - education, degree, university, graduation year -> from profile education
   - start date, when can you start -> "2 weeks notice" or "Flexible"
   - notice period -> "2 weeks"
   - languages -> "English" (add more from profile if available)
   - preferred name -> profile first_name
   - pronouns -> infer from gender or "They/Them"
   - over 18, age verification -> "Yes"
   - background check, consent -> "Yes"
   - agree to terms -> "Yes"
   - salary expectation -> "Open to discussion"
   - skills, tech stack -> extract from profile skills/experience

5. OPEN-ENDED QUESTIONS (confidence=0.6):
   Generate concise responses (2-4 sentences):
   - "Why interested?" / "Why this role?" -> Reference company and role, connect to experience
   - "Tell us about yourself" -> Brief professional summary highlighting relevant experience
   - "Why should we hire you?" -> Use profile's great_fit_pitch or highlight key qualifications
   - "Challenging project" -> Use profile's challenging_project
   - "Strengths" -> Technical skills + relevant soft skills
   - "Weaknesses" -> Something genuine but not disqualifying
   - "Where do you see yourself in 5 years?" -> Growth within company
   - "Questions for us?" -> Express enthusiasm
   - Cover letter -> Generate 2-3 tailored paragraphs

6. FIELD TYPE HANDLING:
   - SELECT/DROPDOWN: Return the EXACT option text from "options" array. Match semantically.
   - CHECKBOX: Return "true" or "false". Consent checkboxes -> "true", newsletters -> "false"
   - RADIO: Return the matching option value string
   - FILE UPLOAD: Set value to "Resume" or "Cover Letter", confidence=0.5, skip=false

---
OUTPUT FORMAT

Return a JSON array with one entry per field:

[
  {{
    "xpath": "<xpath from input>",
    "value": "<generated value>",
    "confidence": <0.0-1.0>,
    "skip": <true only if cannot determine>,
    "skip_reason": "<reason if skipped>"
  }}
]

CONFIDENCE LEVELS:
- 1.0: Direct profile match (name, email, phone)
- 0.9: Derived from profile (years of experience)
- 0.8: Clear semantic match (work auth, demographics)
- 0.7: Reasonable assumption (relocate, consent)
- 0.6: Generated text response
- 0.5: File upload (needs user action)
- 0.4: Default value used

---
WHEN TO SKIP

Only skip (skip=true, value=null) when you genuinely cannot provide a value:
- Specific salary numbers requiring an exact figure
- Reference contact details not in profile
- Personal identifiers (SSN, tax ID, passport)
- CAPTCHA or verification codes

Prefer filling over skipping. The user can adjust values later.
Return ONLY the JSON array. Include ALL fields from input. Match xpath exactly.
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


# =============================================================================
# RSS FEED JOB LINK EXTRACTION
# =============================================================================
# Used to extract actual job application URLs from RSS entries that link to
# aggregator pages (like HN "Who is hiring" comments) rather than direct job pages.

EXTRACT_JOB_LINK_FROM_RSS_PROMPT = """
You are a job link extraction assistant. Your task is to extract the actual job application URL from an RSS feed entry.

═══════════════════════════════════════════════════════════════════════════════
RSS ENTRY CONTENT
═══════════════════════════════════════════════════════════════════════════════
Title: {entry_title}

Description/Content:
{entry_description}

Original Link: {entry_link}

═══════════════════════════════════════════════════════════════════════════════
TASK
═══════════════════════════════════════════════════════════════════════════════
Extract the ACTUAL job application URL from the description content.

PRIORITY ORDER for URL selection:
1. Direct job board URLs (jobs.ashbyhq.com, jobs.lever.co, greenhouse.io, workable.com, etc.)
2. Company careers page URLs (*/careers/*, */jobs/*)
3. Application form URLs
4. LinkedIn job posting URLs (linkedin.com/jobs/*)
5. Company website with job info
6. Email application (return null, we can't automate email)

IGNORE these URLs:
- LinkedIn profile URLs (linkedin.com/in/*)
- GitHub profile URLs (github.com/username without /jobs)
- Twitter/X URLs
- Generic company homepages without job path
- The original RSS entry link if it's just a comment/forum link

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════
Return a JSON object:

{{
  "job_url": "<extracted job application URL or null if not found>",
  "job_title": "<job title extracted from content>",
  "location": "<job location if mentioned>",
  "confidence": <0.0-1.0 how confident you are this is the right URL>,
  "notes": "<any relevant notes about extraction>"
}}

RULES:
- Return the FIRST best matching job URL
- If multiple job URLs exist, pick the most direct application link
- If only email application is available, set job_url to null
- Extract job title from the content
- Set confidence based on how clear the URL extraction was

EXAMPLE INPUT:
Title: "New comment by acme_hiring in Ask HN: Who is hiring?"
Description: "Acme Corp | Senior Engineer | SF | https://jobs.ashbyhq.com/acme/12345"

EXAMPLE OUTPUT:
{{
  "job_url": "https://jobs.ashbyhq.com/acme/12345",
  "job_title": "Senior Engineer",
  "location": "SF",
  "confidence": 1.0,
  "notes": "Direct Ashby job link found"
}}
"""
