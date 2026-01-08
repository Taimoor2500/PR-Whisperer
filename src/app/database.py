from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

# Fallback to SQLite for local development, use DATABASE_URL for production (Supabase/Postgres)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pr_whisperer.db")

# Fix for Postgres URLs starting with "postgres://" (Render/Heroku issue)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class PRReminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String)
    repo = Column(String)
    pr_number = Column(Integer)
    channel = Column(String)
    thread_ts = Column(String)
    reminder_time = Column(DateTime)
    is_sent = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)

