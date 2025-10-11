from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from src.models.feedback.feedback_model import Feedback
from src.models.feedback.feedback_schemas import FeedbackCreate


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


def get_all_feedbacks(db: Session) -> List[Feedback]:
    """Admin: tüm feedbackleri döner."""
    return db.query(Feedback).order_by(Feedback.ts.desc()).all()


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
