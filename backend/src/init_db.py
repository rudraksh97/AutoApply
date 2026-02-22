from .db import engine, Base
from .models import User, Profile, Resume, Job, Feed, Settings

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
