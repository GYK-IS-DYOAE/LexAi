from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.models.auth import user_schemas, user_crud
from src.models.auth.user_model import User
from src.core.db import SessionLocal
from src.api.auth import jwt
from src.api.auth.security import get_current_user
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=user_schemas.UserResponse)
def register(data: user_schemas.RegisterRequest, db: Session = Depends(get_db)):
    if user_crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_crud.create_user(db, data.first_name, data.last_name, data.email, data.password)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_crud.get_user_by_email(db, form_data.username)
    if not user or not user_crud.verify_user(user, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=user_schemas.UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.delete("/delete/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this user")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"detail": f"User {user.email} deleted successfully"}


@router.get("/users", response_model=list[user_schemas.UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=user_schemas.UserResponse)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
