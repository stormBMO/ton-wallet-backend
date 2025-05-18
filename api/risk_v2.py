import uuid as py_uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.token_risk import TokenRisk # SQLAlchemy model
from core.database import get_async_session as get_db # Используем get_async_session и даем ему псевдоним get_db

# Pydantic schema for response
class TokenRiskResponseSchema(BaseModel):
    id: py_uuid.UUID
    token_id: str
    symbol: str
    volatility_30d: float | None
    liquidity_score: float | None
    sentiment_score: float | None
    contract_risk_score: float | None
    overall_risk_score: float | None
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/api/risk_v2",
    tags=["Risk V2"],
)

# Placeholder for RiskV2Service logic
class RiskV2Service:
    @staticmethod
    async def calculate_and_save_risk(token_id: str, db: AsyncSession) -> TokenRisk:
        """
        Placeholder for risk calculation logic.
        Fetches/calculates risk data and saves it to the database.
        Returns the TokenRisk object.
        """
        print(f"RiskV2Service: Recalculating/fetching risk for token_id: {token_id}")

        calculated_data = {
            "symbol": f"SYMBOL_{token_id[:5]}",
            "volatility_30d": 0.1 + (hash(token_id) % 100) / 200.0,
            "liquidity_score": 0.5 + (hash(token_id) % 50) / 100.0,
            "sentiment_score": 0.3 + (hash(token_id) % 70) / 100.0,
            "contract_risk_score": 0.2 + (hash(token_id) % 60) / 100.0,
        }
        calculated_data["overall_risk_score"] = (
            calculated_data["volatility_30d"] * 0.3 +
            calculated_data["liquidity_score"] * 0.3 +
            calculated_data["sentiment_score"] * 0.2 +
            calculated_data["contract_risk_score"] * 0.2
        )

        stmt = select(TokenRisk).where(TokenRisk.token_id == token_id)
        result = await db.execute(stmt)
        token_risk_entry = result.scalars().first()

        if token_risk_entry:
            token_risk_entry.symbol = calculated_data["symbol"]
            token_risk_entry.volatility_30d = calculated_data["volatility_30d"]
            token_risk_entry.liquidity_score = calculated_data["liquidity_score"]
            token_risk_entry.sentiment_score = calculated_data["sentiment_score"]
            token_risk_entry.contract_risk_score = calculated_data["contract_risk_score"]
            token_risk_entry.overall_risk_score = calculated_data["overall_risk_score"]
            # sqlalchemy.func.now() для onupdate должен работать с async, 
            # но если нет, то: token_risk_entry.updated_at = datetime.now(timezone.utc)
        else:
            token_risk_entry = TokenRisk(
                token_id=token_id,
                symbol=calculated_data["symbol"],
                volatility_30d=calculated_data["volatility_30d"],
                liquidity_score=calculated_data["liquidity_score"],
                sentiment_score=calculated_data["sentiment_score"],
                contract_risk_score=calculated_data["contract_risk_score"],
                overall_risk_score=calculated_data["overall_risk_score"]
            )
            db.add(token_risk_entry) # db.add() остается синхронным вызовом
        
        try:
            await db.commit() # Асинхронный commit
            await db.refresh(token_risk_entry) # Асинхронный refresh
        except Exception as e:
            await db.rollback() # Асинхронный rollback
            print(f"Database error in RiskV2Service: {e}")
            raise HTTPException(status_code=500, detail="Error saving token risk data.")
        
        return token_risk_entry


@router.get("/{token_id}", response_model=TokenRiskResponseSchema)
async def get_token_risk_v2(token_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves risk data for a given token ID (CoinGecko ID or Jetton address).
    If the data is stale (older than 5 minutes) or not found, it triggers a recalculation.
    """
    now_utc = datetime.now(timezone.utc)
    five_minutes_ago_utc = now_utc - timedelta(minutes=5)

    stmt = select(TokenRisk).where(TokenRisk.token_id == token_id)
    result = await db.execute(stmt)
    token_risk_data = result.scalars().first()

    if token_risk_data:
        record_updated_at = token_risk_data.updated_at
        if record_updated_at.tzinfo is None:
            record_updated_at = record_updated_at.replace(tzinfo=timezone.utc)

        if record_updated_at >= five_minutes_ago_utc:
            return token_risk_data

    updated_token_risk_data = await RiskV2Service.calculate_and_save_risk(token_id, db)
    return updated_token_risk_data 