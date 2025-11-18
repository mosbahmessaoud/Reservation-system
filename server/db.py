# server\db.py
"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Railway PostgreSQL fix - CRITICAL!
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Only fall back to local in development
if not DATABASE_URL:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("DATABASE_URL not set in production!")
    DATABASE_URL = os.getenv(
        "LOCAL_DATABASE_URL",
        "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db"
    )
    print(f"⚠️ Using local database: {DATABASE_URL[:40]}...")

# Engine configuration with better timeout settings
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": {
        "connect_timeout": 30,  # 30 seconds timeout
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
    })

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
