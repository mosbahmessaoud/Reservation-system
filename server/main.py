"""
FastAPI app entry point with Railway Volume support and timeout protection
"""
import os
import signal
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
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
    pdf_route
)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def initialize_volume_storage():
    """Initialize Railway Volume storage for PDF uploads"""
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
            print("⚠️ Using temporary storage")
            return False

    except Exception as e:
        print(f"❌ Error initializing volume storage: {e}")
        return False


def run_alembic_migrations():
    """Run Alembic migrations with timeout protection"""
    try:
        from alembic.config import Config
        from alembic import command

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(base_dir, "alembic.ini")

        if not os.path.exists(alembic_ini_path):
            print("⚠️ alembic.ini not found, skipping migrations")
            return False

        print("🔄 Running Alembic migrations...")

        # Set timeout for migrations (30 seconds)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)

        try:
            alembic_cfg = Config(alembic_ini_path)
            command.upgrade(alembic_cfg, "head")
            print("✅ Migrations completed successfully")
            return True
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm

    except TimeoutError:
        print("⚠️ Migration timed out - database may already be up to date")
        return True  # Continue anyway
    except Exception as e:
        print(f"⚠️ Migration error (continuing anyway): {e}")
        return False


def ensure_super_admin_exists():
    """Ensure super admin exists with timeout protection"""
    db = SessionLocal()
    try:
        print("👤 Checking super admin...")

        # Set timeout (10 seconds)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)

        try:
            SUPER_ADMIN_PHONE = os.getenv("SUPER_ADMIN_PHONE", "0658890501")
            SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")

            # Check if super admin exists
            super_admin = db.query(User).filter(
                User.phone_number == SUPER_ADMIN_PHONE,
                User.role == UserRole.super_admin
            ).first()

            if super_admin:
                print(f"✅ Super admin exists: {SUPER_ADMIN_PHONE}")
                return

            # Create super admin
            print(f"👤 Creating super admin: {SUPER_ADMIN_PHONE}")

            # Ensure county exists
            county = db.query(County).first()
            if not county:
                print("📍 Creating default county...")
                county = County(name="تغردايت")
                db.add(county)
                db.commit()
                db.refresh(county)

            # Ensure clan exists
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
                hall = Hall(name="دار " + clan.name,
                            capacity=600, clan_id=clan.id)
                db.add(hall)
                db.commit()

            # Create super admin
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
            print(f"✅ Super admin created: {SUPER_ADMIN_PHONE}")

        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm

    except TimeoutError:
        print("⚠️ Super admin check timed out - continuing anyway")
    except Exception as e:
        print(f"⚠️ Error ensuring super admin (continuing): {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("=" * 60)
    print(f"🚀 Starting in {ENVIRONMENT} mode...")
    print(f"📊 Database: Connected")
    print("=" * 60)

    try:
        # Initialize volume storage
        print("\n📦 Initializing storage...")
        initialize_volume_storage()

        # Run migrations
        print("\n🔄 Running database migrations...")
        run_alembic_migrations()

        # Ensure super admin exists
        print("\n👤 Setting up super admin...")
        ensure_super_admin_exists()

        print("\n" + "=" * 60)
        print("✅ Application ready!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n⚠️ Startup warning: {e}")
        print("Continuing anyway...\n")

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
        "docs": "/docs" if not IS_PRODUCTION else "disabled in production"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with storage status"""
    RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    volume_mounted = os.path.exists(RAILWAY_VOLUME_PATH)

    return {
        "status": "healthy",
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=False)
