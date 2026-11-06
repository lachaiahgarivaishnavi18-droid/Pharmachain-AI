import os, hashlib, secrets, hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from .database import get_db
from .models import User

SECRET = os.getenv('JWT_SECRET') or secrets.token_hex(48)
bearer = HTTPBearer()

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}${digest}'

def verify_password(password, encoded):
    salt, expected = encoded.split('$')
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(expected, actual)

def token(user):
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm='HS256')

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=['HS256'])
        user = db.get(User, int(payload['sub']))
        if user is None:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Invalid or expired session')

def roles(*allowed):
    def dependency(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, 'Role does not permit this action')
        return user
    return dependency
