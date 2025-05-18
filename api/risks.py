from fastapi import APIRouter
from schemas.risk import RiskCalculateRequest, RiskCalculateResponse
from services.risk_service import RiskService

router = APIRouter()
service = RiskService()

@router.post("/calculate", response_model=RiskCalculateResponse)
async def calculate_risk(request: RiskCalculateRequest):
    return await service.calculate(request) 