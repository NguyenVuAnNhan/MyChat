from fastapi import APIRouter, HTTPException, Depends, Form, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.session import get_db
from models.User import User

router = APIRouter()

@router.post("/register")
def register_user(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pw = User.hash_password(password)
    user = User(username=username, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created"}

@router.post("/login")
def login(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return {"message": "Login successful"}

@router.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("username")
    response.delete_cookie("user_id")
    return response

@router.get("/me")
async def me(request: Request):
    # Browser sends the HttpOnly session cookie automatically
    user = request.session.get("username")
    if user:
        return {"authenticated": True, "username": user}
    return {"authenticated": False, "username": "Anonymous"}