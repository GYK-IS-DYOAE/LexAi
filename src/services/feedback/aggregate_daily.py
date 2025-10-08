# src/services/feedback/aggregate_daily.py

from sqlalchemy.orm import Session
from models.feedback.feedback_model import Feedback, Action
from core.db import SessionLocal
from datetime import datetime, timedelta
from sqlalchemy import func

def run():
    db: Session = SessionLocal()
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        dislike_count = db.query(func.count()).filter(
            Feedback.vote == -1,
            Feedback.ts >= yesterday,
            Feedback.ts < today
        ).scalar()

        # Basit eşik kontrolü
        if dislike_count >= 10:
            action = Action(
                day=str(today),
                action="reranker_retrain",
                params={"dislike_count": dislike_count},
                triggered=0
            )
            db.add(action)
            db.commit()
            print(f"[+] Action created: {action.action}")
        else:
            print(f"[i] Dislike count {dislike_count}, threshold not reached")

    finally:
        db.close()
