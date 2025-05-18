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

load_dotenv()

DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

app_engine: Optional[AsyncEngine] = None
db_session_factory: Optional[Any] = None # <--- Используем Any для типа

if DATABASE_URL:
    app_engine = create_async_engine(DATABASE_URL, echo=True)
    db_session_factory = async_sessionmaker(app_engine, expire_on_commit=False)
else:
    # Выводим предупреждение, только если это не запуск Alembic
    # (Alembic устанавливает свой URL и не должен зависеть от этого предупреждения)
    if not os.environ.get("ALEMBIC_CONTEXT"):
        print("WARNING: DATABASE_URL is not set via .env. Database features for the main app might be unavailable if not configured elsewhere.")

class Base(DeclarativeBase):
    pass

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if not db_session_factory:
        raise RuntimeError(
            "Database session factory is not initialized. "
            "Ensure DATABASE_URL is set and accessible, or that Alembic context is properly configured."
        )
    async with db_session_factory() as session:
        yield session 