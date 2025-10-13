# src/models/auth/user_model.py

from src.core.base import Base
from sqlalchemy import Column, String, DateTime, Boolean  # Boolean eklendi
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)  # 👈 yeni alan
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
