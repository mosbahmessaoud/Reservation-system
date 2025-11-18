"""
Alembic environment configuration with ENVIRONMENT support
"""
from server.models.reservation_clan_admin import ReservationSpecial, ReservationSpecialStatus
from server.models.reservation import Reservation, ReservationStatus
from server.models.committee import HaiaCommittee, MadaehCommittee
from server.models.food import FoodMenu
from server.models.clan_rules import ClanRules
from server.models.clan_settings import ClanSettings
from server.models.hall import Hall
from server.models.clan import Clan
from server.models.county import County
from server.models.user import User, UserRole
from server.models.notification import Notification, NotificationType

from server.db import Base
from dotenv import load_dotenv
import os
import sys
import re
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add parent directory to path to import server modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# ============================================================
# Use same database selection logic as main.py
# ============================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

if IS_PRODUCTION:
    DATABASE_URL = os.getenv("DATABASE_URL")
    print(f"🔴 Alembic using PRODUCTION database")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set in production!")
else:
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ LOCAL_DATABASE_URL not set, falling back to DATABASE_URL")
        DATABASE_URL = os.getenv("DATABASE_URL")
    else:
        print(f"🟢 Alembic using LOCAL development database")

# Railway PostgreSQL fix - CRITICAL!
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to local database if nothing is set
if not DATABASE_URL:
    if IS_PRODUCTION:
        raise ValueError("DATABASE_URL not set in production!")
    DATABASE_URL = "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db"
    print(f"⚠️ Using default local database")

# Mask password in logs
masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', DATABASE_URL)
print(f"📊 Alembic Database: {masked_url}")

# Override sqlalchemy.url in alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
