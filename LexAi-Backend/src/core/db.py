# src/core/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# DB oturumu için session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
