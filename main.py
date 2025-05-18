from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.risks import router as risks_router
from api.auth import router as auth_router
from services.auth_service import jwt_auth_middleware

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.middleware('http')(jwt_auth_middleware)

app.include_router(risks_router, prefix="/api/risk")
app.include_router(auth_router, prefix="/api/auth")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 