from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .feedback_model import Feedback, Action
from .feedback_schemas import VoteRequest
from typing import Optional

def create_feedback(db: Session, user_id: str, data: VoteRequest) -> Feedback:
    feedback = Feedback(
        user_id=user_id,
        query=data.query,
        response=data.response,
        vote=data.vote,
        action=data.action,
        notes=data.notes
    )
    try:
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Feedback could not be saved: {e}")

def get_feedbacks_by_user(db: Session, user_id: str) -> list[Feedback]:
    return db.query(Feedback).filter(Feedback.user_id == user_id).order_by(Feedback.created_at.desc()).all()

# ✅ Tüm feedback kayıtlarını getir (Admin için)
def get_all_feedbacks(db: Session) -> list[Feedback]:
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()

# ✅ ID’ye göre tek bir feedback getir (Admin için)
def get_feedback_by_id(db: Session, feedback_id: str) -> Optional[Feedback]:
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()

# ✅ Feedback sil (Admin için)
def delete_feedback(db: Session, feedback_id: str) -> bool:
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        return False
    db.delete(feedback)
    db.commit()
    return True
