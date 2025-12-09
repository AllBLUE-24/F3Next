# migrations/env.py
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ---------------------------------------------------------------------------
# Make project root importable so `import schemas` works when Alembic runs
# (migrations/env.py is normally at <project_root>/migrations/env.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # two levels up from this file
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# If the environment contains a DATABASE_URL (common in Docker/CI), prefer it.
# This allows: export DATABASE_URL="postgresql+psycopg2://..." && alembic upgrade head
env_db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
if env_db_url:
    config.set_main_option("sqlalchemy.url", env_db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import your application's MetaData (so Alembic autogenerate can compare)
# ---------------------------------------------------------------------------
target_metadata = None
try:
    # Import the Base and models. Ensure schemas/__init__.py imports model modules
    # so classes register themselves on Base.metadata.
    from schemas.base import Base  # noqa: E402
    import schemas  # noqa: F401,E402

    target_metadata = Base.metadata
except Exception as exc:
    # Keep target_metadata = None if import fails; autogenerate will be disabled.
    # You may want to log or print the exception in advanced setups.
    # For now, preserve original behavior rather than raising here.
    target_metadata = None

# ---------------------------------------------------------------------------
# Other values from the config, defined by the needs of env.py,
# can be acquired using config.get_main_option("name")
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
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
    """Run migrations in 'online' mode (connect to DB and run)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
