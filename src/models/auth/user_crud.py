# src/models/auth/user_crud.py

from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from src.models.auth.user_model import User

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, first_name: str, last_name: str, email: str, password: str):
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash = bcrypt.hash(password.encode("utf-8"))
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def verify_user(user: User, password: str):
    return user and bcrypt.verify(password, user.password_hash)
