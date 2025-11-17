from server.models.reservation_clan_admin import ReservationSpecial
from server.models.reservation import Reservation, ReservationStatus
from server.models.committee import HaiaCommittee, MadaehCommittee
from server.models.food import FoodMenu
from server.models.clan_rules import ClanRules
from server.models.clan_settings import ClanSettings
from server.models.hall import Hall
from server.models.clan import Clan
from server.models.county import County
from server.models.user import User, UserRole
from server.db import Base
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your Base and all models (same as in main.py)

# Import ALL models

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate (THIS IS CRUCIAL!)
target_metadata = Base.metadata

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Railway fix: postgres:// → postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to local database
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:0320@localhost:5432/wedding_db"
    print(f"⚠️ Using local database")
else:
    print(f"✓ Using DATABASE_URL from environment")

# Override the sqlalchemy.url in alembic.ini
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
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
