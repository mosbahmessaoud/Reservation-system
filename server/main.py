"""
FastAPI app entry point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from .auth_utils import get_password_hash
from .db import engine, Base, SessionLocal

# Import models
from .models.user import User, UserRole
from .models.county import County
from .models.clan import Clan
from .models.hall import Hall
from .models.clan_settings import ClanSettings
from .models.clan_rules import ClanRules
from .models.food import FoodMenu
from .models.committee import HaiaCommittee, MadaehCommittee
from .models.reservation import Reservation, ReservationStatus

# Import routes
from .routes import (
    auth,
    super_admin,
    clan_admin,
    reservations,
    grooms,
    food_route,
    public_routes
)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"


def seed_initial_data():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            county = County(name="تغردايت")
            db.add(county)
            db.commit()
            db.refresh(county)

            clan = Clan(name="عشيرة ات الحاج", county_id=county.id)
            db.add(clan)
            db.commit()
            db.refresh(clan)

            settings = ClanSettings(clan_id=clan.id)
            db.add(settings)
            db.commit()

            hall = Hall(name="دار " + clan.name, capacity=500, clan_id=clan.id)
            db.add(hall)
            db.commit()

            super_admin = User(
                phone_number="0658890501",
                password_hash=get_password_hash(
                    os.getenv("SUPER_ADMIN_PASSWORD", "M.superadmin")),
                role=UserRole.super_admin,
                first_name="Super",
                last_name="Admin",
                father_name="Root",
                grandfather_name="Root",
            )
            db.add(super_admin)
            db.commit()
            print("✅ Initial data seeded")
    except Exception as e:
        print(f"❌ Seed error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting in {ENVIRONMENT} mode...")
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    print("✅ Ready!")
    yield
    # Shutdown (add cleanup code here if needed)
    print("👋 Shutting down...")


app = FastAPI(
    title="Wedding Reservation API",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
    lifespan=lifespan
)

# CORS
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if IS_PRODUCTION else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Wedding Reservation API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "FastOpp Demo app is running"}


# Register routers
app.include_router(auth.router)
app.include_router(super_admin.router)
app.include_router(clan_admin.router)
app.include_router(reservations.router)
app.include_router(grooms.router)
app.include_router(food_route.router)
app.include_router(public_routes.router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=False)
