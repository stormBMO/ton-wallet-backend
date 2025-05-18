import uuid
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

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
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TokenRisk(symbol='{self.symbol}', overall_risk_score='{self.overall_risk_score}')>" 