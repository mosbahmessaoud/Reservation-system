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
    public_routes,
    admin_utils
)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"


def ensure_super_admin_exists():
    """
    Ensure super admin exists, create if missing.
    This runs on every startup to handle Railway redeployments.
    """
    db = SessionLocal()
    try:
        SUPER_ADMIN_PHONE = os.getenv("SUPER_ADMIN_PHONE", "0658890501")
        SUPER_ADMIN_PASSWORD = os.getenv(
            "SUPER_ADMIN_PASSWORD", "M.super7admin!2233")

        # Check if super admin exists
        super_admin = db.query(User).filter(
            User.phone_number == SUPER_ADMIN_PHONE,
            User.role == UserRole.super_admin
        ).first()

        if super_admin:
            print(f"✅ Super admin already exists: {SUPER_ADMIN_PHONE}")
            # Optionally update password if it changed
            if os.getenv("RESET_SUPER_ADMIN_PASSWORD") == "true":
                super_admin.password_hash = get_password_hash(
                    SUPER_ADMIN_PASSWORD)
                db.commit()
                print("🔄 Super admin password updated")
            return

        # Super admin doesn't exist, check if we have required data
        county = db.query(County).first()
        if not county:
            print("📍 Creating default county...")
            county = County(name="تغردايت")
            db.add(county)
            db.commit()
            db.refresh(county)

        clan = db.query(Clan).filter(Clan.county_id == county.id).first()
        if not clan:
            print("🏘️ Creating default clan...")
            clan = Clan(name="عشيرة ات الحاج", county_id=county.id)
            db.add(clan)
            db.commit()
            db.refresh(clan)

            # Create clan settings
            settings = ClanSettings(clan_id=clan.id)
            db.add(settings)
            db.commit()

            # Create default hall
            hall = Hall(name="دار " + clan.name, capacity=500, clan_id=clan.id)
            db.add(hall)
            db.commit()

        # Create super admin
        print(f"👤 Creating super admin: {SUPER_ADMIN_PHONE}")
        super_admin = User(
            phone_number=SUPER_ADMIN_PHONE,
            password_hash=get_password_hash(SUPER_ADMIN_PASSWORD),
            role=UserRole.super_admin,
            phone_verified=True,
            first_name="Super",
            last_name="Admin",
            father_name="Root",
            grandfather_name="Root",
        )
        db.add(super_admin)
        db.commit()
        print(f"✅ Super admin created successfully: {SUPER_ADMIN_PHONE}")

    except Exception as e:
        print(f"❌ Error ensuring super admin: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def seed_initial_data():
    """
    Seed initial data only if database is completely empty.
    For Railway, use ensure_super_admin_exists() instead.
    """
    db = SessionLocal()
    try:
        # Check if database is completely empty
        if db.query(User).count() > 0:
            print("ℹ️ Database already has data, skipping full seed")
            return

        print("🌱 Seeding initial data...")

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
            phone_number=os.getenv("SUPER_ADMIN_PHONE", "0658890501"),
            password_hash=get_password_hash(
                os.getenv("SUPER_ADMIN_PASSWORD", "M.super7admin!2002")),
            role=UserRole.super_admin,
            phone_verified=True,
            first_name="Super",
            last_name="Admin",
            father_name="Root",
            grandfather_name="Root",
        )
        db.add(super_admin)
        db.commit()
        print("✅ Initial data seeded successfully")
    except Exception as e:
        print(f"❌ Seed error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting in {ENVIRONMENT} mode...")
    print(f"📊 Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")

    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")

        # Always ensure super admin exists (important for Railway)
        ensure_super_admin_exists()

        # Seed initial data only if database is empty
        seed_initial_data()

        print("✅ Application ready!")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()

    yield

    # Shutdown
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
    return {"status": "healthy", "message": "Wedding Reservation API is running"}


# Register routers
app.include_router(admin_utils.router)
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
