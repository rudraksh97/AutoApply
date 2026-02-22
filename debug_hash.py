from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

try:
    h = get_password_hash("admin123")
    print(f"Hash: {h}")
except Exception as e:
    print(f"Error: {e}")
