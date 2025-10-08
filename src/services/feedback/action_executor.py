# src/services/feedback/action_executor.py

from sqlalchemy.orm import Session
from models.feedback.feedback_model import Action
from core.db import SessionLocal

def run():
    db: Session = SessionLocal()
    try:
        actions = db.query(Action).filter(Action.triggered == 0).all()
        for action in actions:
            if action.action == "reranker_retrain":
                print(f"[+] Executing action: {action.action} on day {action.day}")
                # Burada eğitim veya başka bir işlem tetiklenebilir
                # Örn: subprocess ile başka bir script çağırma vs.

                # Şimdilik sadece işaretleyelim
                action.triggered = 1
                db.commit()
    finally:
        db.close()
