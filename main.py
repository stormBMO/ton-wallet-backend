from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.risks import router as risks_router
from api.auth import router as auth_router
from api.risk_v2 import router as risk_v2_router
from services.auth_service import jwt_auth_middleware
from core.scheduler import start_scheduler, shutdown_scheduler
import asyncio

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("FastAPI startup: Initializing scheduler...")
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    print("FastAPI shutdown: Shutting down scheduler...")
    await shutdown_scheduler()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.middleware('http')(jwt_auth_middleware)

app.include_router(risks_router, prefix="/api/risk")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(risk_v2_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 