"""Alembic migration environment for the main database schema.

Configures Alembic to use the application's database URL from settings_handler
and registers all SQLAlchemy models so that autogenerate can detect schema
changes. Supports both offline (SQL script) and online (live connection)
migration modes.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
import os

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ALL models so they register with Base.metadata
from database import (
    Base, User, UserWhitelist, Role, UserRole,
    Container, ContainerPort, ReservedContainer, ReservedContainerPort,
    Reservation, Computer, HardwareSpec, ReservedHardwareSpec
)
from settings_handler import settings_handler

# this is the Alembic Config object
config = context.config

# Configure the database URL from our settings
config.set_main_option("sqlalchemy.url", settings_handler.get_setting("database.engineUri"))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in offline mode without a live database connection.

    Configures the Alembic context with just the database URL so that
    migration SQL statements are emitted as script output. This allows
    generating migration scripts without requiring a running database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in online mode with a live database connection.

    Creates a SQLAlchemy engine from the Alembic config, opens a connection,
    and runs all pending migrations within a transaction. Uses NullPool to
    avoid keeping idle connections after migration completes.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
