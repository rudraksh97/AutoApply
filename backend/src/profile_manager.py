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
    "education": {
        "degree": "",
        "university": "",
        "field_of_study": "",
        "graduation_year": ""
    }
}

class ProfileManager:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'w') as f:
                json.dump(DEFAULT_PROFILE, f, indent=2)

    def get_profile(self):
        try:
            with open(PROFILE_FILE, 'r') as f:
                data = json.load(f)
                # Merge with default to ensure all keys exist (simple migration)
                merged = DEFAULT_PROFILE.copy()
                # Deep update simplified
                for section in DEFAULT_PROFILE:
                    if section in data:
                        merged[section].update(data[section])
                return merged
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_data):
        with open(PROFILE_FILE, 'w') as f:
            json.dump(profile_data, f, indent=2)

    def get_profile_as_text(self):
        """Returns a string representation suitable for the LLM prompt."""
        p = self.get_profile()
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

        Education:
        {p['education']['degree']} in {p['education']['field_of_study']} from {p['education']['university']} (Graduated: {p['education']['graduation_year']})
        """
        return text.strip()
