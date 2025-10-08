from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID

from src.models.auth import user_schemas, user_crud
from src.models.auth.user_model import User
from src.core.db import SessionLocal
from src.api.auth import jwt

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/auth/register", response_model=user_schemas.UserResponse,
    summary="Register new user",
    description="Yeni bir kullanıcı kaydı oluşturur.")
def register(data: user_schemas.RegisterRequest, db: Session = Depends(get_db)):
    if user_crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = user_crud.create_user(db, data.first_name, data.last_name, data.email, data.password)
    return user

@router.post("/auth/login", summary="Login user", description="Email ve şifre ile giriş yapar, JWT access token döner.")
def login(data: user_schemas.LoginRequest, db: Session = Depends(get_db)):
    user = user_crud.get_user_by_email(db, data.email)
    if not user_crud.verify_user(user, data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/auth/me", response_model=user_schemas.UserResponse,
    summary="Get current user",
    description="Authorization başlığıyla gönderilen JWT token'a göre kullanıcıyı döner.")
def get_me(
    Authorization: str = Header(..., alias="Authorization"), 
    db: Session = Depends(get_db)
):
    token = Authorization.split(" ")[1] if " " in Authorization else Authorization
    payload = jwt.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/auth/delete/{user_id}",
    summary="Delete a user by ID",
    description="JWT token ile kimliği doğrulanmış bir kullanıcının hesabını kalıcı olarak siler.")
def delete_user(
    user_id: str,
    Authorization: str = Header(..., alias="Authorization"), 
    db: Session = Depends(get_db)
):
    token = Authorization.split(" ")[1] if " " in Authorization else Authorization
    payload = jwt.decode_access_token(token)
    if not payload or payload["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized or invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"detail": f"User {user.email} deleted successfully"}

@router.get("/auth/users",
    response_model=list[user_schemas.UserResponse],
    summary="List all users",
    description="Tüm kullanıcıları listeler. Sadece admin paneli için kullanılır.")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.get("/auth/users/{user_id}",
    response_model=user_schemas.UserResponse,
    summary="Get user by ID",
    description="Verilen ID’ye sahip kullanıcıyı getirir. Sadece admin paneli için kullanılır.")
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
