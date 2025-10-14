# src/core/init_db.py

from src.core.db import engine
from src.core.base import Base
from src.models.auth.user_model import User
from src.models.feedback.feedback_model import Feedback

from src.models.conversation.session_model import ConversationSession
from src.models.conversation.message_model import Message


def init_db():
    print("[*] Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("[✓] Tables created successfully.")

if __name__ == "__main__":
    init_db()

