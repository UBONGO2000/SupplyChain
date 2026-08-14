import os
import sys
from logging.config import fileConfig

from alembic import context

# Make the project root importable (this file lives in alembic/, models.py is one level up)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import models  # noqa: E402  (project's SQLAlchemy models)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at the same DATABASE_URL the app itself uses.
# This overrides whatever is hardcoded in alembic.ini.
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Target metadata = the app's real models, so autogenerate can compare
# the live database against models.py and detect drift automatically.
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Reuses the app's own engine from database.py instead of building a
    fresh one via engine_from_config. This matters because database.py
    forces connect_args={"ssl": {"ssl": {}}} for TiDB Cloud (which rejects
    unencrypted connections with error 1105), and engine_from_config has
    no way to know about that requirement -- it only reads plain URL/pool
    options from alembic.ini. Building a separate engine here silently
    lost the SSL requirement, which is exactly why `alembic upgrade head`
    failed during the Render build step.
    """
    import database  # project's own engine, already configured for TiDB Cloud

    connectable = database.engine

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
