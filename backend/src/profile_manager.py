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
    "cover_letter_template": ""
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
                
                return merged
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_data):
        """
        Saves the provided profile data to the JSON file.

        Args:
            profile_data (dict): The complete profile information to persist.
        """
        with open(PROFILE_FILE, 'w') as f:
            json.dump(profile_data, f, indent=2)

    def get_profile_as_text(self):
        """
        Returns a string representation of the profile suitable for the LLM prompt.

        The generated text includes contact info, URLs, demographics, work
        authorization status, experience, and education history.

        Returns:
            str: A formatted block of text.
        """
        p = self.get_profile()
        
        edu_text = ""
        for edu in p.get('education', []):
            edu_text += f"- {edu.get('degree')} in {edu.get('field_of_study')} from {edu.get('university')} ({edu.get('graduation_year')})\n"
            
        exp_text = ""
        for exp in p.get('experience', []):
            exp_text += f"- {exp.get('role')} at {exp.get('company')} ({exp.get('start_date')} - {exp.get('end_date')})\n  {exp.get('description')}\n"

        text = f"""
        Name: {p['basics']['first_name']} {p['basics']['last_name']}
        Email: {p['basics']['email']}
        Phone: {p['basics']['phone']}
        Location: {p['basics']['location']}
        
        LinkedIn: {p['urls']['linkedin']}
        GitHub: {p['urls']['github']}
        Portfolio: {p['urls']['portfolio']}
        
        Gender: {p['demographics']['gender']}
        Nationality: {p['demographics']['nationality']}
        Veteran Status: {p['demographics']['veteran']}
        Disability Status: {p['demographics']['disability']}
        
        Work Authorization:
        - Authorized to work in target country: {p['work_auth']['authorized_in_us']}
        - Requires Sponsorship: {p['work_auth']['requires_sponsorship']}

        Experience:
        {exp_text}

        Education:
        {edu_text}
        
        Pitch:
        {p.get('great_fit_pitch', '')}
        """
        return text.strip()
