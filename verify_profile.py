
import requests
import json
import sys

API_URL = "http://localhost:8000/profile"

payload = {
  "basics": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone": "123-456-7890",
    "location": "Test City"
  },
  "urls": {
    "linkedin": "http://linkedin.com/in/test",
    "github": "http://github.com/test",
    "portfolio": "http://test.com"
  },
  "demographics": {
    "gender": "Male",
    "nationality": "Test",
    "veteran": "I am not a protected veteran",
    "disability": "I do not have a disability"
  },
  "work_auth": {
    "authorized_in_us": True,
    "requires_sponsorship": False
  },
  "education": [
    {
      "degree": "BS CS",
      "university": "Test Uni",
      "field_of_study": "CS",
      "graduation_year": "2024"
    }
  ],
  "experience": [
      {
          "company": "Test Corp",
          "role": "Engineer",
          "start_date": "01/2020",
          "end_date": "Present",
          "description": "Doing testing."
      }
  ],
  "great_fit_pitch": "I am great.",
  "cover_letter_template": "Hello {{company}}"
}

try:
    print("Sending request to", API_URL)
    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        print("Success: Profile saved.")
    else:
        print(f"Failed: {response.status_code} - {response.text}")
        sys.exit(1)
        
    # Verify GET
    response = requests.get(API_URL)
    data = response.json()
    if len(data['experience']) == 1 and data['experience'][0]['company'] == 'Test Corp':
         print("Verification Passed: Data retrieved correctly.")
    else:
         print("Verification Failed: Retrieved data mismatch.")
         print(json.dumps(data, indent=2))
         sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
