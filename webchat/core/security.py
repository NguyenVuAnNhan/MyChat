from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from models.User import User
import os
from dotenv import load_dotenv
from itsdangerous import URLSafeSerializer, BadSignature
import json

load_dotenv()  


SECRET = os.getenv("SECRET")
print("SECRET KEY-sec:", SECRET)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user

serializer = URLSafeSerializer(secret_key=SECRET, salt="starlette.sessions")

def decode_session(session_cookie: str) -> dict:

    print("Session Cookie:", session_cookie)
    session_cookie = session_cookie.strip('"')

    try:
        data = serializer.loads(session_cookie)  # only ONCE
        return data  # already a Python dict
    except BadSignature:
        print("Signature error")
        return {}