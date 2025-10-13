from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel

from src.core.db import SessionLocal
from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.models.feedback.feedback_schemas import FeedbackResponse
from src.models.feedback import feedback_crud


router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)


# ✅ DB bağlantısı
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🧩 Vote body modeli
class VoteRequest(BaseModel):
    vote: str  # "like" veya "dislike"


# ✅ Kullanıcı cevaba oy verir (body üzerinden)
@router.patch(
    "/{feedback_id}/vote",
    summary="Vote for feedback",
    description="Kullanıcı belirli bir cevaba oy verir (like/dislike).",
)
def vote_feedback(
    feedback_id: UUID,
    data: VoteRequest,  # 👈 Body'den JSON olarak alıyoruz
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    feedback = feedback_crud.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # 👇 Yalnızca o feedback’in sahibi oy verebilir
    if feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only vote for your own feedbacks")

    # 👇 Oy kontrolü
    if data.vote not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="Vote must be 'like' or 'dislike'")

    # 👇 Veritabanında güncelle
    feedback.vote = data.vote
    db.commit()
    db.refresh(feedback)

    return {
        "detail": f"Vote updated to '{data.vote}'",
        "feedback_id": str(feedback.id),
        "vote": feedback.vote
    }

@router.get(
    "/user/{user_id}",
    response_model=list[FeedbackResponse],
    summary="List feedbacks by user (Admin only)",
    description="Sadece admin kullanıcılar, belirli bir kullanıcıya ait feedback'leri görebilir."
)
def list_feedbacks_by_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
 
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    feedbacks = feedback_crud.get_feedbacks_by_user(db, user_id=user_id)
    if not feedbacks:
        raise HTTPException(status_code=404, detail="No feedbacks found for this user")

    return feedbacks


@router.get(
    "/all",
    response_model=list[FeedbackResponse],
    summary="List all feedbacks (Admin only)",
    description="Tüm kullanıcıların geri bildirimlerini listeler. Sadece admin erişimine açıktır.",
)
def list_all_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return feedback_crud.get_all_feedbacks(db)


# ✅ Feedback ID'ye göre getir (herkes erişebilir)
@router.get(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Get feedback by ID",
    description="Belirli bir feedback ID'sine göre geri bildirimi getirir.",
)
def get_feedback_by_id(
    feedback_id: UUID,
    db: Session = Depends(get_db)
):
    feedback = feedback_crud.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback
