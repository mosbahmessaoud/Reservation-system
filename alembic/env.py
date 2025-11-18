"""
Alembic environment configuration
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
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add parent directory to path to import server modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your Base and all models for autogenerate support

# Set target metadata for autogenerate support
target_metadata = Base.metadata

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

# Override sqlalchemy.url in alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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


# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode.

#     In this scenario we need to create an Engine
#     and associate a connection with the context.

#     """
#     configuration = config.get_section(config.config_ini_section, {})
#     configuration["sqlalchemy.url"] = DATABASE_URL

#     connectable = engine_from_config(
#         configuration,
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection,
#             target_metadata=target_metadata,
#             compare_type=True,
#             compare_server_default=True,
#         )

#         with context.begin_transaction():
#             context.run_migrations()
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL

    # Add connection timeout settings
    configuration["sqlalchemy.connect_args"] = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

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
