from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Base(AsyncAttrs, DeclarativeBase):
    pass

class TokenRisk(Base):
    __tablename__ = "token_risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False)
    volatility_30d = Column(Float)
    liquidity_score = Column(Float)
    sentiment_score = Column(Float)
    contract_risk_score = Column(Float)
    overall_risk_score = Column(Float)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
