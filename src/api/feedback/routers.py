from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from src.core.db import SessionLocal
from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.models.feedback import feedback_schemas, feedback_crud

router = APIRouter(tags=["Feedback"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Kullanıcı kendi feedback'ini oluşturur
@router.post(
    "/feedback",
    response_model=feedback_schemas.FeedbackResponse,
    summary="Submit feedback",
    description="Bir sorgu-yanıt çifti için kullanıcı oyu ve notları ile geri bildirim oluşturur."
)
def submit_feedback(
    data: feedback_schemas.VoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return feedback_crud.create_feedback(db, user_id=current_user.id, data=data)


# ✅ Giriş yapan kullanıcının kendi feedback'lerini listeler
@router.get(
    "/feedbacks/me",
    response_model=list[feedback_schemas.FeedbackResponse],
    summary="List my feedbacks",
    description="Giriş yapan kullanıcıya ait tüm geri bildirimleri listeler."
)
def list_my_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return feedback_crud.get_feedbacks_by_user(db, user_id=current_user.id)


# 🔐 Admin: Tüm kullanıcıların feedback'lerini listeler
@router.get(
    "/feedbacks",
    response_model=list[feedback_schemas.FeedbackResponse],
    summary="List all feedbacks (Admin only)",
    description="Tüm kullanıcıların geri bildirimlerini listeler. Sadece admin içindir."
)
def list_all_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return feedback_crud.get_all_feedbacks(db)


# ✅ Feedback ID'ye göre getir (herkes görebilir diyorsan kullanıcı kontrolü gerekmez)
@router.get(
    "/feedbacks/{feedback_id}",
    response_model=feedback_schemas.FeedbackResponse,
    summary="Get feedback by ID",
    description="Belirli bir feedback ID'sine göre tek bir geri bildirimi getirir."
)
def get_feedback_by_id(
    feedback_id: UUID,
    db: Session = Depends(get_db)
):
    feedback = feedback_crud.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


# 🔐 Admin: Feedback sil
@router.delete(
    "/feedbacks/{feedback_id}",
    summary="Delete feedback by ID (Admin only)",
    description="Belirli bir feedback kaydını siler. Sadece admin erişimine açıktır."
)
def delete_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    success = feedback_crud.delete_feedback(db, feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return {"detail": f"Feedback {feedback_id} deleted successfully"}
