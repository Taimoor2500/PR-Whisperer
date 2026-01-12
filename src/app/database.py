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


class UserMapping(Base):
    """Maps GitHub usernames to Slack user IDs for proper tagging."""
    __tablename__ = "user_mappings"

    id = Column(Integer, primary_key=True, index=True)
    github_username = Column(String, unique=True, index=True)
    slack_user_id = Column(String)  # Slack user ID like U12345678


def get_slack_user_id(github_username: str) -> str | None:
    """Look up Slack user ID from GitHub username."""
    db = SessionLocal()
    try:
        mapping = db.query(UserMapping).filter(
            UserMapping.github_username == github_username
        ).first()
        return mapping.slack_user_id if mapping else None
    finally:
        db.close()


def set_user_mapping(github_username: str, slack_user_id: str) -> bool:
    """Create or update a GitHub → Slack user mapping."""
    db = SessionLocal()
    try:
        existing = db.query(UserMapping).filter(
            UserMapping.github_username == github_username
        ).first()
        
        if existing:
            existing.slack_user_id = slack_user_id
        else:
            new_mapping = UserMapping(
                github_username=github_username,
                slack_user_id=slack_user_id
            )
            db.add(new_mapping)
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error setting user mapping: {e}")
        return False
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

