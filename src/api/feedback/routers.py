from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from src.models.feedback import feedback_schemas, feedback_crud
from src.models.feedback.feedback_model import Feedback
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

def get_current_user(
    Authorization: str = Header(..., alias="Authorization"), 
    db: Session = Depends(get_db)
) -> User:
    token = Authorization.split(" ")[1] if " " in Authorization else Authorization
    payload = jwt.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/feedback",
    response_model=feedback_schemas.FeedbackResponse,
    summary="Submit feedback",
    description="Bir sorgu-yanıt çifti için kullanıcı oyu ve notları ile geri bildirim oluşturur.")
def submit_feedback(
    data: feedback_schemas.VoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return feedback_crud.create_feedback(db, current_user.id, data)

@router.get("/feedbacks/me",
    response_model=list[feedback_schemas.FeedbackResponse],
    summary="List my feedbacks",
    description="Giriş yapan kullanıcıya ait tüm geri bildirimleri listeler.")
def list_my_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return feedback_crud.get_feedbacks_by_user(db, current_user.id)

@router.get("/feedbacks",
    response_model=list[feedback_schemas.FeedbackResponse],
    summary="List all feedbacks",
    description="Tüm kullanıcıların tüm geri bildirimlerini listeler. Sadece admin paneli içindir.")
def list_all_feedbacks(db: Session = Depends(get_db)):
    return feedback_crud.get_all_feedbacks(db)

@router.get("/feedbacks/{feedback_id}",
    response_model=feedback_schemas.FeedbackResponse,
    summary="Get feedback by ID",
    description="Belirli bir feedback ID'sine göre tek bir geri bildirimi getirir.")
def get_feedback_by_id(feedback_id: str, db: Session = Depends(get_db)):
    feedback = feedback_crud.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

@router.delete("/feedbacks/{feedback_id}",
    summary="Delete feedback by ID",
    description="Feedback ID'si verilen geri bildirimi siler. Sadece admin için.")
def delete_feedback(feedback_id: str, db: Session = Depends(get_db)):
    success = feedback_crud.delete_feedback(db, feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"detail": f"Feedback {feedback_id} deleted successfully"}
