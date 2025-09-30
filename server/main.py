"""
FastAPI app entry point. Includes all routers, creates tables, and seeds initial data.
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .auth_utils import get_password_hash
from .routes import food_route
from .routes.auth import router
from .routes.clan_admin import router
from .db import engine, Base, SessionLocal

# Import ALL models FIRST before any database operations
from .models.user import User, UserRole
from .models.county import County
from .models.clan import Clan
from .models.hall import Hall
from .models.clan_settings import ClanSettings
from .models.clan_rules import ClanRules
from .models.food import FoodMenu
from .models.committee import HaiaCommittee, MadaehCommittee
from .models.reservation import Reservation, ReservationStatus

from .routes import (
    auth,
    super_admin,
    clan_admin,
    reservations,
    grooms,
    food_route,
    public_routes
)

# Load .env file
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Debug prints (only in development)
if not IS_PRODUCTION:
    print("TWILIO_ACCOUNT_SID:", os.getenv("TWILIO_ACCOUNT_SID"))
    print("TWILIO_PHONE_NUMBER:", os.getenv("TWILIO_PHONE_NUMBER"))
    print("DATABASE_URL:", os.getenv("DATABASE_URL", "Not set")[:30] + "...")

# Initialize FastAPI app
app = FastAPI(
    title="Wedding Reservation API",
    description="API for managing wedding reservations and clan operations",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if IS_PRODUCTION else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Simple health check endpoint


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "message": "Wedding Reservation API is running",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

# Root endpoint


@app.get("/")
async def root():
    return {
        "message": "Wedding Reservation API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if not IS_PRODUCTION else "disabled"
    }

# Register routers
app.include_router(auth.router)
app.include_router(super_admin.router)
app.include_router(clan_admin.router)
app.include_router(reservations.router)
app.include_router(grooms.router)
app.include_router(food_route.router)
app.include_router(public_routes.router)

# Create tables on startup


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print(f"Starting application in {ENVIRONMENT} mode...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified")

    # Seed initial data
    seed_initial_data()
    print("Initial data seeded")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    print("Shutting down application...")

# Initial seed data


def seed_initial_data():
    """Seed database with initial data if empty"""
    db = SessionLocal()

    try:
        if db.query(User).count() == 0:
            # Create County
            county = County(name="تغردايت")
            db.add(county)
            db.commit()
            db.refresh(county)

            # Create Clan
            clan = Clan(name="عشيرة ات الحاج", county_id=county.id)
            db.add(clan)
            db.commit()
            db.refresh(clan)

            # Create Clan Settings
            settings = ClanSettings(clan_id=clan.id)
            db.add(settings)
            db.commit()

            # Create Hall
            hall = Hall(name="دار " + clan.name, capacity=500, clan_id=clan.id)
            db.add(hall)
            db.commit()

            # Super Admin
            super_admin_password = os.getenv(
                "SUPER_ADMIN_PASSWORD", "M.superadmin")
            super_admin = User(
                phone_number="0658890501",
                password_hash=get_password_hash(super_admin_password),
                role=UserRole.super_admin,
                first_name="Super",
                last_name="Admin",
                father_name="Root",
                grandfather_name="Root",
            )
            db.add(super_admin)
            db.commit()

            print("Initial data seeded successfully!")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()
