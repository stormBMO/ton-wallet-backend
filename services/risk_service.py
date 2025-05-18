from schemas.risk import RiskCalculateRequest, RiskCalculateResponse
import numpy as np
import pandas as pd
from typing import Any

class RiskService:
    async def calculate(self, request: RiskCalculateRequest) -> RiskCalculateResponse:
        # Для MVP: сгенерируем случайные данные для расчёта sigma30d
        np.random.seed(42)
        prices = np.cumprod(1 + np.random.normal(0, 0.02, 30)) * 1.0
        returns = pd.Series(prices).pct_change().dropna()
        sigma30d = float(np.std(returns) * np.sqrt(30))
        return RiskCalculateResponse(
            sigma30d=sigma30d,
            liquidity_score=75,  # mock
            contract_risk=3,     # mock
            sentiment_index=10   # mock
        ) 