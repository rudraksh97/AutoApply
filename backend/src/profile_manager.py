"""
User profile management for the AutoApply application.

This module handles the storage of personal details, work authorization, 
and education history. It also provides utilities to convert the structured
profile into a textual format for LLM consumption.
"""

import json
import os

PROFILE_FILE = "data/profile.json"

DEFAULT_PROFILE = {
    "basics": {
        "first_name": "", 
        "last_name": "", 
        "email": "", 
        "phone": "", 
        "location": ""
    },
    "urls": {
        "linkedin": "", 
        "github": "", 
        "portfolio": ""
    },
    "demographics": {
        "gender": "Prefer not to say", 
        "race": "Prefer not to say",
        "nationality": "", 
        "veteran": "I am not a protected veteran", 
        "disability": "I do not have a disability"
    },
    "work_auth": {
        "authorized_in_us": True, 
        "requires_sponsorship": False
    },
    "education": [],
    "experience": [],
    "great_fit_pitch": "",
    "cover_letter_template": "",
    "why_us": "",
    "challenging_project": "",
    "uploaded_resume_path": "",
    "uploaded_resume_filename": "",
    "use_uploaded_resume": False,
    "custom_template_filename": ""
}

class ProfileManager:
    """
    Manages the user's personal and professional profile data.

    Provides methods to load, save, and export the profile as a descriptive
    string used by the browser agent during the application process.
    """
    def __init__(self):
        """Initializes the manager and ensures the profile data file exists."""
        self._ensure_file()

    def _ensure_file(self):
        """Creates the data directory and profile JSON file if they do not exist."""
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'w') as f:
                json.dump(DEFAULT_PROFILE, f, indent=2)

    def get_profile(self):
        """
        Retrieves the user's profile data.

        Returns:
            dict: The complete profile dictionary, merged with defaults for safety.
        """
        try:
            with open(PROFILE_FILE, 'r') as f:
                data = json.load(f)
                # Merge with default to ensure all keys exist
                merged = DEFAULT_PROFILE.copy()
                
                for key, value in data.items():
                    # Migration: If education is a dict (old format), convert to list
                    if key == "education" and isinstance(value, dict):
                         # If it's a dict with empty strings (default old state), make it an empty list or single item
                         if not value.get("university"): # Heuristic for empty
                             merged[key] = []
                         else:
                             merged[key] = [value]
                         continue
                         
                    # If the key is in default profile and types match (both dicts), update. 
                    # Otherwise (lists or primitives), overwrite.
                    if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key].update(value)
                    else:
                        merged[key] = value
                
                if not merged.get("uploaded_resume_filename") and merged.get("uploaded_resume_path"):
                     merged["uploaded_resume_filename"] = os.path.basename(merged["uploaded_resume_path"])

                return merged
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_data):
        """
        Saves the provided profile data to the JSON file.
        Uses a merge strategy to preserve existing keys that might be missing
        from the incoming data (e.g., internal paths).

        Args:
            profile_data (dict): The complete profile information to persist.
        """
        existing = self.get_profile()
        
        # Deep merge for standard sections
        for key, value in profile_data.items():
            if key in existing and isinstance(existing[key], dict) and isinstance(value, dict):
                existing[key].update(value)
            else:
                existing[key] = value
        
        with open(PROFILE_FILE, 'w') as f:
            json.dump(existing, f, indent=2)

    def update_from_resume_data(self, parsed_data: dict, resume_path: str = None):
        """
        Updates the profile with data parsed from a resume.

        Args:
            parsed_data: The structured JSON data returned by ResumeParser.
            resume_path: Optional path to the resume file to set as 'uploaded_resume_path'.
        """
        profile = self.get_profile()
        
        # Deep merge strategy
        if parsed_data.get("basics"):
            profile["basics"].update(parsed_data["basics"])
        if parsed_data.get("urls"):
            profile["urls"].update(parsed_data["urls"])
        if parsed_data.get("education"):
            profile["education"] = parsed_data["education"]
        if parsed_data.get("experience"):
            profile["experience"] = parsed_data["experience"]
            
        if resume_path:
            profile["uploaded_resume_path"] = resume_path
            
        self.save_profile(profile)

    def get_profile_as_text(self):
        """
        Returns a string representation of the profile suitable for the LLM prompt.

        The generated text includes contact info, URLs, demographics, work
        authorization status, experience, and education history. Field labels
        are structured to match common job application form fields.

        Returns:
            str: A formatted block of text.
        """
        p = self.get_profile()
        
        edu_text = ""
        for edu in p.get('education', []):
            edu_text += f"  - {edu.get('degree')} in {edu.get('field_of_study')} from {edu.get('university')} ({edu.get('graduation_year')})\n"
        if not edu_text:
            edu_text = "  (No education entries)\n"
            
        exp_text = ""
        for exp in p.get('experience', []):
            exp_text += f"  - {exp.get('role')} at {exp.get('company')} ({exp.get('start_date')} - {exp.get('end_date')})\n    {exp.get('description')}\n"
        if not exp_text:
            exp_text = "  (No experience entries)\n"

        # Structure with explicit field labels matching common form fields
        text = f"""
=== PERSONAL INFORMATION ===
first_name: {p['basics']['first_name']}
last_name: {p['basics']['last_name']}
full_name: {p['basics']['first_name']} {p['basics']['last_name']}
email: {p['basics']['email']}
phone: {p['basics']['phone']}
location: {p['basics']['location']}

=== ONLINE PROFILES ===
linkedin: {p['urls']['linkedin']}
github: {p['urls']['github']}
portfolio: {p['urls']['portfolio']}

=== DEMOGRAPHICS (EEO/Voluntary Disclosure) ===
gender: {p['demographics']['gender']}
race: {p['demographics'].get('race', 'Prefer not to say')}
nationality: {p['demographics']['nationality']}
veteran_status: {p['demographics']['veteran']}
disability_status: {p['demographics']['disability']}

=== WORK AUTHORIZATION ===
authorized_to_work: {'Yes' if p['work_auth']['authorized_in_us'] else 'No'}
requires_sponsorship: {'Yes' if p['work_auth']['requires_sponsorship'] else 'No'}

=== EXPERIENCE ===
{exp_text}
=== EDUCATION ===
{edu_text}
=== APPLICATION RESPONSES ===
great_fit_pitch: {p.get('great_fit_pitch', '(Not provided)')}

why_us: {p.get('why_us', '(Not provided)')}

challenging_project: {p.get('challenging_project', '(Not provided)')}
"""
        return text.strip()
