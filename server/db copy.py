##backend\db.py

"""
Database connection and session setup for SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Update this with your PostgreSQL connection URL
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db"

# SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()
# Add this function for FastAPI dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
