from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from models.User import User
import os
from dotenv import load_dotenv
from itsdangerous import Signer, BadSignature
import json

load_dotenv()  


SECRET = os.getenv("SECRET")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user

def decode_session(session_cookie: str) -> dict:
    signer = Signer(SECRET)
    try:
        # Unsign and decode the raw session value
        raw_data = signer.unsign(session_cookie)
        return json.loads(raw_data)
    except BadSignature:
        return {}