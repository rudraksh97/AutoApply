from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import bcrypt
import os
import json

# Load config for JWT settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "development.json")

try:
    with open(CONFIG_PATH, "r") as f:
        _config = json.load(f)
except FileNotFoundError:
    _config = {}

# JWT Settings
SECRET_KEY = _config.get("jwt_secret", "your-secret-key-please-change-in-production")
ALGORITHM = _config.get("algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day expiration

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Use bcrypt to check password
    try:
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
            
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    # Use bcrypt to hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
