import json
import os
import sys
from sqlalchemy.orm import Session
from .db import SessionLocal, engine
from .models import User, Profile, Job, Feed, Settings, Resume
import bcrypt

def get_password_hash(password):
    # Retrieve salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def migrate_data():
    db = SessionLocal()
    try:
        print("Starting migration...")
        
        # 1. Create Default Admin User
        admin_email = "admin@example.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            print("Creating default admin user...")
            admin_user = User(
                email=admin_email,
                username="admin",
                hashed_password=get_password_hash("admin123"),
                roles=["admin", "basic", "customer"] # Superuser
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        
        # 2. Migrate Profile
        profile_data = load_json("data/profile.json")
        if profile_data:
            print("Migrating profile...")
            # Check if profile exists
            existing_profile = db.query(Profile).filter(Profile.user_id == admin_user.id).first()
            if not existing_profile:
                # Extract fields
                basics = profile_data.get("basics", {})
                urls = profile_data.get("urls", {})
                
                new_profile = Profile(
                    user_id=admin_user.id,
                    first_name=basics.get("first_name"),
                    last_name=basics.get("last_name"),
                    email=basics.get("email"),
                    phone=basics.get("phone"),
                    location=basics.get("location"),
                    linkedin=urls.get("linkedin"),
                    github=urls.get("github"),
                    portfolio=urls.get("portfolio"),
                    skills=profile_data.get("skills"),
                    experience=profile_data.get("experience"),
                    education=profile_data.get("education")
                )
                db.add(new_profile)
                
                # Migrate Resumes metadata
                from datetime import datetime
                
                def parse_dt(dt_str):
                    if not dt_str: return datetime.utcnow()
                    try:
                        return datetime.fromisoformat(dt_str)
                    except:
                        return datetime.utcnow()

                pdf_resumes = profile_data.get("pdf_resumes", [])
                for res in pdf_resumes:
                    existing_resume = db.query(Resume).filter(Resume.id == res["id"]).first()
                    if not existing_resume:
                         db.add(Resume(
                             id=res["id"],
                             user_id=admin_user.id,
                             filename=res["filename"],
                             path=res["path"],
                             type="PDF",
                             created_at=parse_dt(res.get("created_at"))
                         ))
                
                text_resumes = profile_data.get("text_resumes", [])
                for res in text_resumes:
                    existing_resume = db.query(Resume).filter(Resume.id == res["id"]).first()
                    if not existing_resume:
                         db.add(Resume(
                             id=res["id"],
                             user_id=admin_user.id,
                             filename=res["filename"],
                             path=res["path"],
                             type="TXT",
                             created_at=parse_dt(res.get("created_at"))
                         ))

        # 3. Migrate Config/Settings
        config_data = load_json("data/config.json")
        if config_data:
             print("Migrating settings...")
             existing_settings = db.query(Settings).filter(Settings.user_id == admin_user.id).first()
             if not existing_settings:
                 db.add(Settings(
                     user_id=admin_user.id,
                     config_data=config_data,
                     include_global_feeds=True
                 ))
        
        # 4. Migrate Jobs (if any source available, assuming none for now or empty)
        # TODO: Implement if there's a jobs.json source
        
        db.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
