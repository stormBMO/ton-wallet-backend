from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    async_sessionmaker, # Это функция-фабрика
    AsyncEngine, 
    AsyncSession
    # AsyncSessionMaker - убираем, т.к. вызывает ошибку импорта
)
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os
from typing import Optional, AsyncGenerator, Any # <--- ДОБАВЛЕНО Any

# Определяем путь к корневой папке проекта и к .env файлу
# os.path.dirname(__file__) -> /path/to/project/core
# os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) -> /path/to/project
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Загружаем переменные из .env, находящегося в корне проекта
# override=True означает, что значения из .env перезапишут уже существующие переменные окружения
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    print(f"DEBUG: core/database.py: Loaded .env from {DOTENV_PATH}")
else:
    print(f"DEBUG: core/database.py: .env file not found at {DOTENV_PATH}")

DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
print(f"DEBUG: core/database.py: os.getenv('DATABASE_URL') is: '{DATABASE_URL}'")

app_engine: Optional[AsyncEngine] = None
db_session_factory: Optional[Any] = None # <--- Используем Any для типа
SessionLocal: Optional[Any] = None # Определяем SessionLocal

if DATABASE_URL:
    app_engine = create_async_engine(DATABASE_URL, echo=True)
    db_session_factory = async_sessionmaker(app_engine, expire_on_commit=False)
    SessionLocal = db_session_factory # Присваиваем db_session_factory к SessionLocal
else:
    # Выводим предупреждение, только если это не запуск Alembic
    # (Alembic устанавливает свой URL и не должен зависеть от этого предупреждения)
    if not os.environ.get("ALEMBIC_CONTEXT"):
        print("WARNING: DATABASE_URL is not set via .env. Database features for the main app might be unavailable if not configured elsewhere.")

class Base(DeclarativeBase):
    pass

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if not SessionLocal: # Используем SessionLocal здесь для консистентности
        raise RuntimeError(
            "Database session factory (SessionLocal) is not initialized. "
            "Ensure DATABASE_URL is set and accessible, or that Alembic context is properly configured."
        )
    async with SessionLocal() as session: # Используем SessionLocal здесь
        yield session 