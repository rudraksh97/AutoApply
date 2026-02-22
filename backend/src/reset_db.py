from .db import engine, Base
from .models import User, Profile, Resume, Job, Feed, Settings

def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped.")
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

if __name__ == "__main__":
    reset_db()
