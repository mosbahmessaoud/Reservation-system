"""
FastAPI app entry point with Railway Volume support and local development database
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


def get_database_url():
    """
    Get the appropriate database URL based on environment
    """
    if IS_PRODUCTION:
        db_url = os.getenv("DATABASE_URL")
        print(f"🔴 Using PRODUCTION database")
        if not db_url:
            raise ValueError("DATABASE_URL not set in production!")
    else:
        db_url = os.getenv("LOCAL_DATABASE_URL")
        if not db_url:
            print("⚠️ LOCAL_DATABASE_URL not set, falling back to DATABASE_URL")
            db_url = os.getenv("DATABASE_URL")
        else:
            print(f"🟢 Using LOCAL development database")

    if not db_url:
        raise ValueError("No database URL configured!")

    # Railway PostgreSQL uses postgres:// but SQLAlchemy needs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Mask password in logs
    masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', db_url)
    print(f"📊 Database: {masked_url}")

    return db_url


def initialize_volume_storage():
    """
    Initialize Railway Volume storage for PDF uploads
    Creates necessary directories on startup
    """
    try:
        if IS_PRODUCTION:
            RAILWAY_VOLUME_PATH = os.getenv(
                "RAILWAY_VOLUME_MOUNT_PATH", "/data")
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
        else:
            # Development mode - use local temp directory
            UPLOAD_DIR = Path("./temp_uploads/pdfs")
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Local upload directory ready: {UPLOAD_DIR}")
            return True

    except Exception as e:
        print(f"❌ Error initializing volume storage: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_alembic_migrations():
    """
    Run Alembic migrations programmatically
    This is safer than Base.metadata.create_all() in production
    """
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
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully")
        return True
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

        if not SUPER_ADMIN_PASSWORD:
            print("⚠️ WARNING: SUPER_ADMIN_PASSWORD not set in environment!")
            return

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
            print("🏛️ Creating default county...")
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


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     print("=" * 60)
#     print(f"🚀 Starting in {ENVIRONMENT} mode...")
#     get_database_url()  # This will print the database info
#     print("=" * 60)

#     try:
#         # Initialize volume storage first
#         print("\n📦 Initializing storage...")
#         volume_ready = initialize_volume_storage()
#         if not volume_ready and IS_PRODUCTION:
#             print("⚠️ WARNING: Running in production without persistent storage!")

#         # Run Alembic migrations FIRST - before any database queries
#         print("\n🔄 Running database migrations...")
#         migration_success = run_alembic_migrations()

#         if not migration_success:
#             if IS_PRODUCTION:
#                 print("❌ CRITICAL: Migrations failed in production!")
#                 raise Exception(
#                     "Database migration failed - cannot start application")
#             else:
#                 # Fallback to create_all only in development
#                 print("⚠️ Migrations failed, falling back to create_all...")
#                 Base.metadata.create_all(bind=engine)
#                 print("✅ Database tables created/verified")

#         # ONLY AFTER migrations are complete, check/create super admin
#         print("\n👤 Checking super admin...")
#         ensure_super_admin_exists()

#         print("\n" + "=" * 60)
#         print("✅ Application ready!")
#         print(f"🌍 Environment: {ENVIRONMENT}")
#         print(f"📍 Server: http://127.0.0.1:8000")
#         print(f"📚 Docs: http://127.0.0.1:8000/docs" if not IS_PRODUCTION else "📚 Docs: Disabled in production")
#         print("=" * 60)

#     except Exception as e:
#         print(f"\n❌ Startup error: {e}")
#         import traceback
#         traceback.print_exc()
#         if IS_PRODUCTION:
#             # In production, fail fast if startup fails
#             raise

#     yield

#     # Shutdown
#     print("\n👋 Shutting down...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("=" * 60)
    print(f"🚀 Starting in {ENVIRONMENT} mode...")
    get_database_url()  # This will print the database info
    print("=" * 60)

    try:
        # Initialize volume storage first
        print("\n📦 Initializing storage...")
        volume_ready = initialize_volume_storage()
        if not volume_ready and IS_PRODUCTION:
            print("⚠️ WARNING: Running in production without persistent storage!")

        # Check if migrations should be skipped
        skip_migrations = os.getenv(
            "SKIP_MIGRATIONS", "false").lower() == "true"

        if skip_migrations:
            print("\n⚠️ ⚠️ ⚠️ SKIPPING MIGRATIONS (SKIP_MIGRATIONS=true) ⚠️ ⚠️ ⚠️")
            print("⚠️ This is a temporary bypass - ensure database schema is correct!")
            print("⚠️ Remove SKIP_MIGRATIONS after resolving migration issues!")

            # Still ensure tables exist using create_all as fallback
            try:
                print("🔄 Ensuring database tables exist...")
                Base.metadata.create_all(bind=engine)
                print("✅ Database tables verified")
            except Exception as e:
                print(f"⚠️ Error creating tables: {e}")
                if IS_PRODUCTION:
                    print("⚠️ Continuing anyway due to SKIP_MIGRATIONS flag...")
        else:
            # Normal migration flow
            print("\n🔄 Running database migrations...")
            migration_success = run_alembic_migrations()

            if not migration_success:
                if IS_PRODUCTION:
                    print("❌ CRITICAL: Migrations failed in production!")
                    print("💡 TIP: Set SKIP_MIGRATIONS=true to bypass temporarily")
                    print("💡 Then investigate and fix the migration issue")
                    # Don't raise - allow app to start anyway for emergency recovery
                    print("⚠️ Attempting to continue without migrations...")
                    try:
                        Base.metadata.create_all(bind=engine)
                        print("✅ Database tables created/verified as fallback")
                    except Exception as fallback_error:
                        print(f"❌ Fallback also failed: {fallback_error}")
                        raise Exception(
                            "Cannot start - both migrations and fallback failed")
                else:
                    # Fallback to create_all only in development
                    print("⚠️ Migrations failed, falling back to create_all...")
                    Base.metadata.create_all(bind=engine)
                    print("✅ Database tables created/verified")

        # ONLY AFTER migrations/schema setup is complete, check/create super admin
        print("\n👤 Checking super admin...")
        ensure_super_admin_exists()

        print("\n" + "=" * 60)
        print("✅ Application ready!")
        print(f"🌍 Environment: {ENVIRONMENT}")
        print(f"📍 Server: http://127.0.0.1:8000")
        if not IS_PRODUCTION:
            print(f"📚 Docs: http://127.0.0.1:8000/docs")
        else:
            print("📚 Docs: Disabled in production")
        if skip_migrations:
            print("⚠️ WARNING: Running with SKIP_MIGRATIONS=true")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Startup error: {e}")
        import traceback
        traceback.print_exc()
        if IS_PRODUCTION and not skip_migrations:
            # In production, fail fast if startup fails (unless migrations skipped)
            raise
        elif IS_PRODUCTION:
            print("⚠️ Continuing despite error due to SKIP_MIGRATIONS flag...")

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
        "docs": "/docs" if not IS_PRODUCTION else None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with storage status"""
    import os
    from pathlib import Path

    if IS_PRODUCTION:
        RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
        volume_mounted = os.path.exists(RAILWAY_VOLUME_PATH)
        storage_info = {
            "volume_mounted": volume_mounted,
            "volume_path": RAILWAY_VOLUME_PATH if volume_mounted else "not mounted"
        }
    else:
        storage_info = {
            "volume_mounted": False,
            "storage_path": "./temp_uploads",
            "note": "Using local development storage"
        }

    return {
        "status": "healthy",
        "message": "Wedding Reservation API is running",
        "environment": ENVIRONMENT,
        "database": "local" if not IS_PRODUCTION else "railway",
        "storage": storage_info
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
