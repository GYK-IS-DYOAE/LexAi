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

# ✅ DB oturumu
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Kayıt ol
@router.post("/register", response_model=user_schemas.UserResponse, summary="Register new user")
def register(data: user_schemas.RegisterRequest, db: Session = Depends(get_db)):
    if user_crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_crud.create_user(db, data.first_name, data.last_name, data.email, data.password)


# ✅ Giriş yap
@router.post("/login", summary="Login and get JWT token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_crud.get_user_by_email(db, form_data.username)
    if not user or not user_crud.verify_user(user, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


# ✅ Me endpoint (JWT üzerinden kendini öğren)
@router.get("/me", response_model=user_schemas.UserResponse, summary="Get current user info")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ✅ Kullanıcıyı admin yap (sadece admin)
@router.patch("/users/{user_id}/make-admin", summary="Grant admin role to user", status_code=status.HTTP_200_OK)
def make_admin(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can perform this action")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    db.commit()
    db.refresh(user)
    return {"detail": f"{user.email} is now an admin ✅"}


# ✅ Admin yetkisini kaldır (sadece admin)
@router.patch("/users/{user_id}/remove-admin", summary="Revoke admin role from user", status_code=status.HTTP_200_OK)
def remove_admin(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can perform this action")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = False
    db.commit()
    db.refresh(user)
    return {"detail": f"{user.email} is no longer an admin 🚫"}


# ✅ Kullanıcı silme (kendi hesabını veya adminse başkasını)
@router.delete("/delete/{user_id}", summary="Delete user")
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


# ✅ Admin-only: tüm kullanıcıları listele
@router.get("/users", response_model=list[user_schemas.UserResponse], summary="List all users (Admin only)")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return db.query(User).all()


# ✅ Kullanıcıyı ID'ye göre getir (sadece kendi veya admin)
@router.get("/users/{user_id}", response_model=user_schemas.UserResponse, summary="Get user by ID")
def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
