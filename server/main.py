"""
FastAPI app entry point with Railway Volume support
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import re
from sqlalchemy import text

from server.routes import pdf_route

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
from .models.reservation_clan_admin import ReservationSpecial, ReservationSpecialStatus
from .models.notification import Notification, NotificationType


# Import routes
from .routes import (
    auth,
    super_admin,
    clan_admin,
    reservations,
    grooms,
    food_route,
    public_routes,
    admin_utils,
    pdf_route,
    notification


)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"


def initialize_volume_storage():
    """
    Initialize Railway Volume storage for PDF uploads
    Creates necessary directories on startup
    """
    try:
        RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
        UPLOAD_DIR = Path(RAILWAY_VOLUME_PATH) / "uploads" / "pdfs"

        if os.path.exists(RAILWAY_VOLUME_PATH):
            print(f"✅ Railway volume found at: {RAILWAY_VOLUME_PATH}")
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Upload directory ready: {UPLOAD_DIR}")

            # Check write permissions
            test_file = UPLOAD_DIR / ".test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print("✅ Volume is writable")
            except Exception as e:
                print(f"⚠️ Warning: Volume may not be writable: {e}")

            return True
        else:
            print(f"⚠️ Railway volume not found at {RAILWAY_VOLUME_PATH}")
            print("⚠️ Using temporary storage - files will be lost on redeploy")
            print("💡 To fix: Add a volume in Railway dashboard mounted at /data")
            return False

    except Exception as e:
        print(f"❌ Error initializing volume storage: {e}")
        import traceback
        traceback.print_exc()
        return False


# def run_alembic_migrations():
#     """
#     Run Alembic migrations programmatically
#     This is safer than Base.metadata.create_all() in production
#     """
#     try:
#         from alembic.config import Config
#         from alembic import command
#         import os

#         # Get the directory containing this file
#         base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         alembic_ini_path = os.path.join(base_dir, "alembic.ini")

#         if not os.path.exists(alembic_ini_path):
#             print("⚠️ alembic.ini not found, skipping migrations")
#             return False

#         print("🔄 Running Alembic migrations...")
#         alembic_cfg = Config(alembic_ini_path)
#         command.upgrade(alembic_cfg, "head")
#         print("✅ Migrations completed successfully")
#         return True
#     except Exception as e:
#         print(f"❌ Migration error: {e}")
#         import traceback
#         traceback.print_exc()
#         return False

def run_alembic_migrations():
    """
    Run Alembic migrations programmatically with retry logic
    This is safer than Base.metadata.create_all() in production
    """
    import time
    from sqlalchemy.exc import OperationalError

    try:
        from alembic.config import Config
        from alembic import command
        import os

        # Get the directory containing this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(base_dir, "alembic.ini")

        if not os.path.exists(alembic_ini_path):
            print("⚠️ alembic.ini not found, skipping migrations")
            return False

        print("🔄 Running Alembic migrations...")
        alembic_cfg = Config(alembic_ini_path)

        # Retry logic for database connection
        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                command.upgrade(alembic_cfg, "head")
                print("✅ Migrations completed successfully")
                return True
            except OperationalError as e:
                if "Connection timed out" in str(e) or "could not connect" in str(e):
                    if attempt < max_retries - 1:
                        print(
                            f"⚠️ Database connection failed (attempt {attempt + 1}/{max_retries})")
                        print(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(
                            f"❌ Database connection failed after {max_retries} attempts")
                        raise
                else:
                    raise

    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def ensure_super_admin_exists():
    """
    Ensure super admin exists, create if missing.
    This runs on every startup to handle Railway redeployments.
    """
    db = SessionLocal()
    try:
        SUPER_ADMIN_PHONE = os.getenv("SUPER_ADMIN_PHONE", "0658890501")
        SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")

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
            clan = Clan(name="عشيرة ات الحاج مسعود ", county_id=county.id)
            db.add(clan)
            db.commit()
            db.refresh(clan)

            # Create clan settings
            settings = ClanSettings(clan_id=clan.id)
            db.add(settings)
            db.commit()

            # Create default hall
            hall = Hall(name="دار " + clan.name, capacity=600, clan_id=clan.id)
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

        clan = Clan(name="عشيرة ات الحاج مسعود ", county_id=county.id)
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
                os.getenv("SUPER_ADMIN_PASSWORD")),
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
    print("=" * 60)
    print(f"🚀 Starting in {ENVIRONMENT} mode...")
    print(f"📊 Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
    print("=" * 60)

    try:
        # Initialize volume storage first
        print("\n📦 Initializing storage...")
        volume_ready = initialize_volume_storage()
        if not volume_ready and IS_PRODUCTION:
            print("⚠️ WARNING: Running in production without persistent storage!")

        # # Run Alembic migrations
        # print("\n🔄 Running database migrations...")
        # migration_success = run_alembic_migrations()

        # if not migration_success and not IS_PRODUCTION:
        #     # Fallback to create_all only in development if migrations fail
        #     print("⚠️ Migrations failed, falling back to create_all...")
        #     Base.metadata.create_all(bind=engine)
        #     print("✅ Database tables created/verified")

        # Always ensure super admin exists (important for Railway)
        print("\n👤 Checking super admin...")
        ensure_super_admin_exists()

        # Seed initial data only if database is empty
        print("\n🌱 Checking initial data...")
        seed_initial_data()

        print("\n" + "=" * 60)
        print("✅ Application ready!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Startup error: {e}")
        import traceback
        traceback.print_exc()

    yield

    # Shutdown
    print("\n👋 Shutting down...")


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
    return {
        "status": "ok",
        "message": "Wedding Reservation API",
        "environment": ENVIRONMENT,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with storage status"""
    import os
    from pathlib import Path

    RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    volume_mounted = os.path.exists(RAILWAY_VOLUME_PATH)

    return {
        "status": "healthy",
        "message": "Wedding Reservation API is running",
        "environment": ENVIRONMENT,
        "storage": {
            "volume_mounted": volume_mounted,
            "volume_path": RAILWAY_VOLUME_PATH if volume_mounted else "not mounted"
        }
    }


# Register routers
app.include_router(admin_utils.router)
app.include_router(auth.router)
app.include_router(super_admin.router)
app.include_router(clan_admin.router)
app.include_router(reservations.router)
app.include_router(grooms.router)
app.include_router(food_route.router)
app.include_router(public_routes.router)
app.include_router(pdf_route.router)
app.include_router(notification.router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=False)
