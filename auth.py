import bcrypt
from datetime import datetime,timedelta,timezone
from jose import jwt
from config import settings
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends,HTTPException
from sqlalchemy.orm import Session
from jose import JWTError
from models import User
from database import get_db

def create_access_token(data:dict):
    to_encode=data.copy()
    expire=datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp":expire})
    return jwt.encode(to_encode,settings.SECRET_KEY,algorithm=settings.ALGORITHM)

def hash_password(password:str):
    salt=bcrypt.gensalt()
    hashed_password=bcrypt.hashpw(password.encode("utf-8"),salt)
    return hashed_password.decode("utf-8")

def verify_password(plain_password:str,hashed_password:str):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),hashed_password.encode("utf-8")
    )

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="login")
def get_current_user(
    token:str = Depends(oauth2_scheme),db:Session=Depends(get_db)
):
    try:
        payload=jwt.decode(
            token,settings.SECRET_KEY,algorithms=[settings.ALGORITHM]
        )
        email=payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401,detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401,detail="Invalid token")
    user=db.query(User).filter(User.email==email).first()
    if not user:
        raise HTTPException(status_code=400,detail="Not found")
    
    return user

def role_required(required_role: str,current_user: User = Depends(get_current_user)):
    if current_user.role != required_role:
        raise HTTPException(status_code=403, detail="Access Denied")
    return current_user

