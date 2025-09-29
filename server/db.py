
# backend\server\db.py
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

# ✅ Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Railway PostgreSQL fix: Change postgres:// to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ Fallback to local PostgreSQL or SQLite for development
if not DATABASE_URL:
    # Try local PostgreSQL first (from your original config)
    local_db = os.getenv(
        "LOCAL_DATABASE_URL", "postgresql+psycopg2://postgres:036063@localhost:5432/wedding_db")
    DATABASE_URL = local_db
    print(
        f"⚠️ No DATABASE_URL found, using local database: {DATABASE_URL[:30]}...")

# ✅ Engine configuration
engine_kwargs = {
    "pool_pre_ping": True,  # Verify connections before using
    "pool_recycle": 3600,   # Recycle connections after 1 hour
}

# Add SQLite-specific configuration
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL-specific configuration
    engine_kwargs.update({
        "pool_size": 10,        # Maximum connections in pool
        "max_overflow": 20,     # Maximum overflow connections
        "pool_timeout": 30,     # Timeout for getting connection
    })

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# ✅ Dependency for getting database session


def get_db():
    """
    Dependency function to get database session.
    Use in FastAPI routes with Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Optional: Test database connection


def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# Test connection on import (only in development)
if os.getenv("ENVIRONMENT") != "production":
    test_connection()
