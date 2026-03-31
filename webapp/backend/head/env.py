"""Alembic migration environment for the HEAD schema tracking branch.

This is the default Alembic environment generated for schema-only migration
tracking. Unlike the main alembic/env.py, it does not import application
models or configure a database URL from settings_handler, so target_metadata
is None and autogenerate is not supported. It serves as a baseline template
for offline and online migration execution.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in offline mode without a live database connection.

    Configures the Alembic context with just the database URL so that
    migration SQL statements are emitted as script output. This allows
    generating migration scripts without requiring a running database
    or DBAPI driver.
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

    Creates a SQLAlchemy engine from the Alembic ini config, opens a
    connection, and executes all pending migrations within a transaction.
    Uses NullPool to avoid keeping idle connections after migration
    completes.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
