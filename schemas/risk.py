from pydantic import BaseModel

class RiskCalculateRequest(BaseModel):
    token_address: str

class RiskCalculateResponse(BaseModel):
    sigma30d: float
    liquidity_score: int
    contract_risk: int
    sentiment_index: int 