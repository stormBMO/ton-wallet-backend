import os
from dotenv import load_dotenv
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Устанавливаем флаг контекста Alembic ДО импорта core.database
os.environ["ALEMBIC_CONTEXT"] = "1"

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Явно получаем DATABASE_URL из окружения ПОСЛЕ load_dotenv()
# loaded_database_url = "postgresql://admin:admin2025!@localhost:5432/ton_wallet_db" # <-- Возвращаем как было
loaded_database_url = os.getenv("DATABASE_URL")

# --- ОТЛАДОЧНАЯ ПЕЧАТЬ --- 
# Печатаем то, что ФАКТИЧЕСКИ загружено в loaded_database_url из окружения
print(f"DEBUG: alembic/env.py: os.getenv('DATABASE_URL') after load_dotenv() is: '{loaded_database_url}'")
# --- КОНЕЦ ОТЛАДОЧНОЙ ПЕЧАТИ ---

if not loaded_database_url:
    # Эта ошибка будет более информативной, если .env не загрузился или пуст
    raise ValueError(
        f"Alembic: DATABASE_URL not found in environment after attempting to load .env from {dotenv_path}. "
        "Please ensure .env file exists, is in the correct location, and contains the DATABASE_URL."
    )

# Устанавливаем URL для Alembic программно. 
# Это переопределит sqlalchemy.url из alembic.ini, если он был ${...}
config.set_main_option("sqlalchemy.url", loaded_database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Импортируем Base ПОСЛЕ загрузки .env, чтобы DATABASE_URL в core.database был установлен
from core.database import Base 
import models.token_risk 
target_metadata = Base.metadata

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
    # Теперь get_main_option должен вернуть URL, который мы установили выше
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # async_engine_from_config использует sqlalchemy.url из config по умолчанию
    # которое мы установили через config.set_main_option()
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), 
        prefix="sqlalchemy.", # это говорит ему искать sqlalchemy.url
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
