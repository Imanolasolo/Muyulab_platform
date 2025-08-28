import hashlib
import jwt
import datetime

SECRET_KEY = "CAMBIAESTESECRETO"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def create_jwt(user):
    payload = {
        "user_id": user["id"],
        "nombre": user["nombre"],
        "email": user["email"],
        "rol": user["rol"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_jwt(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
