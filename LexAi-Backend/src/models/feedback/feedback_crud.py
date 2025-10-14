from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import cast, String
from typing import Optional, List
from src.models.feedback.feedback_model import Feedback
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.models.auth.user_model import User
from uuid import UUID


def create_feedback(db: Session, data: FeedbackCreate) -> Feedback:
    """Yeni feedback oluşturur."""
    feedback = Feedback(
        user_id=data.user_id,
        question_id=data.question_id,
        answer_id=data.answer_id,
        question_text=data.question_text,
        answer_text=data.answer_text,
        vote=data.vote,
        model=data.model,
    )
    try:
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Feedback could not be saved: {e}")


def get_feedbacks_by_user(db: Session, user_id: str) -> List[Feedback]:
    """Belirli bir kullanıcıya ait tüm feedback kayıtlarını döner."""
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.ts.desc())
        .all()
    )



def get_all_feedbacks(db: Session):
    """Admin paneli için tüm feedback kayıtlarını kullanıcı bilgileriyle birlikte döner."""
    feedbacks = db.query(Feedback).order_by(Feedback.ts.desc()).all()

    # Tüm kullanıcıları tek seferde çek
    users = db.query(User).all()
    # UUID -> user eşleşmesi (hem UUID hem string key olarak)
    user_map = {}
    for u in users:
        try:
            user_map[str(u.id)] = u
            user_map[UUID(str(u.id))] = u
        except Exception:
            continue

    result = []
    for feedback in feedbacks:
        user = user_map.get(str(feedback.user_id)) or user_map.get(UUID(str(feedback.user_id))) if feedback.user_id else None

        if user:
            user_email = user.email
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        else:
            user_email = "—"
            user_name = "Bilinmiyor"

        result.append({
            "id": str(feedback.id),
            "question_id": str(feedback.question_id) if feedback.question_id else None,
            "answer_id": str(feedback.answer_id) if feedback.answer_id else None,
            "question_text": feedback.question_text,
            "answer_text": feedback.answer_text,
            "vote": feedback.vote,
            "user_id": str(feedback.user_id) if feedback.user_id else None,
            "model": feedback.model,
            "ts": feedback.ts,
            "user_email": user_email,
            "user_name": user_name,
        })

    return result

def get_feedback_by_id(db: Session, feedback_id: str) -> Optional[Feedback]:
    """ID'ye göre tek bir feedback döner."""
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()


def delete_feedback(db: Session, feedback_id: str) -> bool:
    """Admin: Feedback siler."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        return False
    db.delete(feedback)
    db.commit()
    return True
