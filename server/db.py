#server\db.py
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

# Railway PostgreSQL fix
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to local database
if not DATABASE_URL:
    DATABASE_URL = os.getenv(
        "LOCAL_DATABASE_URL",
        "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db"
    )
    print(f"⚠️ Using local database: {DATABASE_URL[:40]}...")

# Engine configuration
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
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

# def test_connection():
#     """Test database connection"""
#     try:
#         with engine.connect() as conn:
#             conn.execute(text("SELECT 1"))
#         print("✅ Database connected successfully")
#         return True
#     except Exception as e:
#         print(f"❌ Database connection failed: {e}")
#         return False
