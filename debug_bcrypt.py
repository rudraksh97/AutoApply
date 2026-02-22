import bcrypt

try:
    password = b"super secret password"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    print(f"Bcrypt hash: {hashed}")
except Exception as e:
    print(f"Bcrypt Error: {e}")

from passlib.context import CryptContext
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    h = pwd_context.hash("test")
    print(f"Passlib hash: {h}")
except Exception as e:
    print(f"Passlib Error: {e}")
