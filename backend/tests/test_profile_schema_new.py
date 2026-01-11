
from fastapi.testclient import TestClient
from api.server import app
from api.schemas.models import ProfileData

client = TestClient(app)

def test_save_and_get_profile_new_schema():
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

    # Test POST
    response = client.post("/profile/", json=payload)
    assert response.status_code == 200, f"POST failed: {response.text}"
    assert response.json() == {"status": "saved"}

    # Test GET
    response = client.get("/profile/")
    assert response.status_code == 200
    data = response.json()
    
    # Verify new fields
    assert len(data['education']) == 1
    assert data['education'][0]['degree'] == "BS CS"
    assert len(data['experience']) == 1
    assert data['experience'][0]['company'] == "Test Corp"
    assert data['great_fit_pitch'] == "I am great."
