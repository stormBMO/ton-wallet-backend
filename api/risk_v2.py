import uuid as py_uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.token_risk import TokenRisk # SQLAlchemy model
from core.database import get_async_session as get_db # Используем get_async_session и даем ему псевдоним get_db
from services.risk_v2_service import RiskV2Service # Новый импорт

# Pydantic schema for response
class TokenRiskResponseSchema(BaseModel):
    id: py_uuid.UUID
    token_id: str
    symbol: str
    volatility_30d: float | None
    liquidity_score: float | None # Higher is better (e.g. liquidity ratio percent)
    sentiment_score: float | None # Higher is better (e.g. 0-100, 100 positive)
    contract_risk_score: float | None # Higher is riskier (e.g. 0-100, 100 high risk)
    overall_risk_score: float | None # Higher is riskier (e.g. 0-100, 100 high risk)
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/api/risk_v2",
    tags=["Risk V2"],
)

async def _calculate_and_save_risk_data(token_id: str, db: AsyncSession) -> TokenRisk:
    """
    Fetches risk data using RiskV2Service, then saves or updates it in the database.
    Returns the TokenRisk ORM object.
    """
    risk_calculator_service = RiskV2Service()
    print(f"[API Endpoint] Recalculating/fetching risk for token_id: {token_id} using external service.")

    try:
        # 1. Рассчитать данные с помощью сервиса
        # Сервис возвращает словарь:
        # {
        #     "token_id": token_id,
        #     "symbol": symbol,
        #     "volatility_30d_percent": round(volatility_30d, 2),
        #     "liquidity_ratio_percent": round(liquidity_score, 2),
        #     "contract_safety_score": round(contract_risk_score, 2), # 0-100, 100=good
        #     "sentiment_score": round(sentiment_score, 2), # 0-100, 50=neutral, 100=good
        #     "overall_risk_score": round(overall_risk_score, 2) # 0-100, 100=high risk
        # }
        calculated_data = await risk_calculator_service.calculate_risk(token_id)
    except Exception as e:
        # Обработка ошибок от сервиса calculate_risk (например, если внешние API недоступны)
        print(f"Error calling RiskV2Service for {token_id}: {e}")
        # Решаем, что делать. Можно вернуть ошибку 503 или пытаться отдать старые данные, если есть.
        # Пока что пробрасываем HTTPException, чтобы указать на проблему с расчетом.
        raise HTTPException(status_code=503, detail=f"Error calculating risk data for token: {e}")

    # 2. Найти или создать запись в БД
    stmt = select(TokenRisk).where(TokenRisk.token_id == token_id)
    result = await db.execute(stmt)
    token_risk_entry = result.scalars().first()

    if token_risk_entry:
        # Обновить существующую запись
        token_risk_entry.symbol = calculated_data["symbol"]
        token_risk_entry.volatility_30d = calculated_data["volatility_30d_percent"]
        token_risk_entry.liquidity_score = calculated_data["liquidity_ratio_percent"]
        token_risk_entry.sentiment_score = calculated_data["sentiment_score"]
        # contract_safety_score (100=good) -> contract_risk_score (100=bad)
        token_risk_entry.contract_risk_score = 100.0 - calculated_data["contract_safety_score"]
        token_risk_entry.overall_risk_score = calculated_data["overall_risk_score"]
        # updated_at должен обновиться автоматически благодаря onupdate=func.now() в модели
    else:
        # Создать новую запись
        token_risk_entry = TokenRisk(
            token_id=token_id, # calculated_data["token_id"] будет таким же
            symbol=calculated_data["symbol"],
            volatility_30d=calculated_data["volatility_30d_percent"],
            liquidity_score=calculated_data["liquidity_ratio_percent"],
            sentiment_score=calculated_data["sentiment_score"],
            contract_risk_score=100.0 - calculated_data["contract_safety_score"],
            overall_risk_score=calculated_data["overall_risk_score"]
            # id и updated_at будут установлены автоматически
        )
        db.add(token_risk_entry)
    
    try:
        await db.commit()
        await db.refresh(token_risk_entry)
    except Exception as e:
        await db.rollback()
        print(f"Database error saving risk data for {token_id}: {e}")
        raise HTTPException(status_code=500, detail="Error saving token risk data to database.")
    
    return token_risk_entry


@router.get("/{token_id}", response_model=TokenRiskResponseSchema)
async def get_token_risk_v2(token_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves risk data for a given token ID (CoinGecko ID or Jetton address).
    If the data is stale (older than 5 minutes) or not found, it triggers a recalculation
    using the new RiskV2Service.
    """
    now_utc = datetime.now(timezone.utc)
    # TODO: Сделать время жизни кэша (5 минут) настраиваемым, например, из .env
    cache_ttl_minutes = 5 
    stale_threshold_utc = now_utc - timedelta(minutes=cache_ttl_minutes)

    stmt = select(TokenRisk).where(TokenRisk.token_id == token_id)
    result = await db.execute(stmt)
    token_risk_data = result.scalars().first()

    if token_risk_data:
        record_updated_at = token_risk_data.updated_at
        # Убедимся, что updated_at имеет timezone info для корректного сравнения
        if record_updated_at.tzinfo is None:
            # Предполагаем UTC, если не указано (согласно func.now() в модели)
            record_updated_at = record_updated_at.replace(tzinfo=timezone.utc) 

        if record_updated_at >= stale_threshold_utc:
            print(f"[API Endpoint] Serving fresh cached data for {token_id} from DB.")
            return token_risk_data
        else:
            print(f"[API Endpoint] Cached data for {token_id} is stale. Recalculating.")
    else:
        print(f"[API Endpoint] No data for {token_id} in DB. Calculating.")

    # Данные не найдены или устарели, вызываем функцию для расчета и сохранения
    try:
        updated_token_risk_data = await _calculate_and_save_risk_data(token_id, db)
        return updated_token_risk_data
    except HTTPException as http_exc: # Пробрасываем HTTPException дальше
        raise http_exc
    except Exception as e: # Ловим другие неожиданные ошибки
        print(f"Unexpected error during risk calculation for {token_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing token risk.") 