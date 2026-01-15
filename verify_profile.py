import json
import os
import sys

# Ensure backend source is in path
sys.path.append('backend')
from src.profile_manager import ProfileManager

def verify():
    print(f"Current working directory: {os.getcwd()}")
    profile_path = "data/profile.json"
    
    if os.path.exists(profile_path):
        print(f"Found profile.json at: {os.path.abspath(profile_path)}")
        try:
            with open(profile_path, 'r') as f:
                data = json.load(f)
            
            print("\n--- Profile Structure Check ---")
            keys = data.keys()
            print(f"Top level keys: {list(keys)}")
            
            # Check for multi-resume fields
            multi_resume_keys = ["pdf_resumes", "text_resumes", "current_pdf_resume_id", "current_text_resume_id"]
            for k in multi_resume_keys:
                status = "Present" if k in data else "MISSING"
                print(f"{k}: {status}")
            
            # Check for content
            print(f"\nPDF Resumes count: {len(data.get('pdf_resumes', []))}")
            print(f"Text Resumes count: {len(data.get('text_resumes', []))}")
            
            # Verification via Manager
            pm = ProfileManager()
            profile = pm.get_profile()
            print("\n--- ProfileManager Integration Check ---")
            print(f"Manager reports PDF resumes: {len(profile.get('pdf_resumes', []))}")
            
        except Exception as e:
            print(f"Error reading profile.json: {e}")
    else:
        print(f"CRITICAL: profile.json NOT FOUND at {profile_path}")

if __name__ == "__main__":
    verify()
