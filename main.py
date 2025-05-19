from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.risks import router as risks_router
from api.auth import router as auth_router
from api.risk_v2 import router as risk_v2_router
from services.auth_service import jwt_auth_middleware
from core.scheduler import start_scheduler, shutdown_scheduler
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполняется перед запуском приложения (startup)
    print("Приложение запускается...")
    start_scheduler() # Запускаем планировщик
    yield
    # Код, который выполняется после остановки приложения (shutdown)
    print("Приложение останавливается...")
    shutdown_scheduler() # Останавливаем планировщик

app = FastAPI(
    title="Ton Wallet Backend",
    description="API for Ton Wallet application, including token risk assessment.",
    version="0.1.0",
    lifespan=lifespan # Новый способ управления событиями startup/shutdown в FastAPI
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.middleware('http')(jwt_auth_middleware)

app.include_router(risks_router, prefix="/api/risk")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(risk_v2_router)

# Пример простого эндпоинта
@app.get("/")
async def read_root():
    return {"message": "Welcome to Ton Wallet Backend API"}

# Если у вас есть код для создания таблиц через Alembic или SQLAlchemy metadata,
# он обычно вызывается отдельно или управляется миграциями.
# Например:
# from core.database import engine, Base
# async def create_tables():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
# В FastAPI с lifespan это можно сделать так:
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await create_tables() # Если нужно создавать таблицы при старте (обычно не для Alembic)
#     start_scheduler()
#     yield
#     shutdown_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 