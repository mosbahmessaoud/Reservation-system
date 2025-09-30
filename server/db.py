"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Railway PostgreSQL fix: Change postgres:// to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to local database for development
if not DATABASE_URL:
    local_db = os.getenv(
        "LOCAL_DATABASE_URL",
        "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db"
    )
    DATABASE_URL = local_db
    print(f"Using local database: {DATABASE_URL[:40]}...")

# Engine configuration
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# Database-specific configuration
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
    })

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for getting database session


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
