import asyncio
import random # Для мок-данных
# import httpx # Потенциально для асинхронных HTTP запросов в будущем

# Заглушки для конфигурации API (в реальном приложении это будет в .env или config.py)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
TONAPI_URL = "https://tonapi.io/v2"
# BEARER_TOKEN_TONAPI = "YOUR_TONAPI_BEARER_TOKEN" # Пример, если нужен токен

class RiskV2Service:
    """
    Сервис для расчета различных метрик риска для токенов.
    """

    async def _fetch_coingecko_historical_prices(self, token_id_coingecko: str, days: int = 30) -> list[float]:
        """
        Заглушка для получения исторических цен с CoinGecko.
        В реальной реализации здесь будет HTTP запрос к API CoinGecko.
        """
        print(f"[RiskV2Service-Mock] Запрос исторических цен для {token_id_coingecko} за {days} дней.")
        # Имитация задержки сети
        await asyncio.sleep(0.1)
        # Мок-данные: генерируем случайные цены
        prices = [100.0 + (random.random() - 0.5) * 20 for _ in range(days)]
        if not prices:
            # Пример обработки случая, когда данные не найдены
            print(f"[RiskV2Service-Mock] Исторические цены для {token_id_coingecko} не найдены.")
            return []
        return prices

    async def _fetch_coingecko_market_data(self, token_id_coingecko: str) -> dict | None:
        """
        Заглушка для получения рыночных данных (объем, капитализация) с CoinGecko.
        В реальной реализации здесь будет HTTP запрос к API CoinGecko.
        """
        print(f"[RiskV2Service-Mock] Запрос рыночных данных для {token_id_coingecko}.")
        # Имитация задержки сети
        await asyncio.sleep(0.1)
        # Мок-данные
        # Может вернуть None, если токен не найден
        if random.random() < 0.05: # 5% шанс, что токен не найден
             print(f"[RiskV2Service-Mock] Рыночные данные для {token_id_coingecko} не найдены.")
             return None
        return {
            "total_volume": random.uniform(100000, 5000000),
            "market_cap": random.uniform(10000000, 500000000),
            "symbol": f"MOCK_{token_id_coingecko[:3].upper()}"
        }

    async def _fetch_tonapi_jetton_holders_count(self, jetton_address: str) -> int | None:
        """
        Заглушка для получения количества холдеров Jetton с TonAPI.
        В реальной реализации здесь будет HTTP запрос к TonAPI.
        """
        print(f"[RiskV2Service-Mock] Запрос количества холдеров для Jetton {jetton_address}.")
        # Имитация задержки сети
        await asyncio.sleep(0.1)
        # Мок-данные
        # Может вернуть None, если адрес не Jetton или ошибка API
        if not jetton_address.startswith("EQ"): # Грубая проверка, что это может быть адрес
             print(f"[RiskV2Service-Mock] {jetton_address} не похож на Jetton адрес для TonAPI.")
             return 0 # Или None, в зависимости от того, как хотим обрабатывать

        if random.random() < 0.1: # 10% шанс на ошибку/ненайденный jetton
            print(f"[RiskV2Service-Mock] Не удалось получить кол-во холдеров для {jetton_address}.")
            return None
        return random.randint(100, 10000)

    def _calculate_std_dev(self, prices: list[float]) -> float:
        """
        Расчет стандартного отклонения (сигма).
        """
        if not prices or len(prices) < 2:
            return 0.0
        mean = sum(prices) / len(prices)
        variance = sum([(price - mean) ** 2 for price in prices]) / (len(prices) -1) # Используем N-1 для выборки
        return variance ** 0.5

    async def calculate_risk(self, token_id: str) -> dict:
        """
        Рассчитывает различные метрики риска для указанного token_id.
        token_id может быть ID от CoinGecko или адресом Jetton для TonAPI.
        Логика определения типа token_id здесь упрощена.
        """
        print(f"[RiskV2Service] Начало расчета риска для token_id: {token_id}")

        # Предполагаем, что token_id может быть как идентификатором Coingecko, так и адресом Jetton.
        # В реальном приложении может потребоваться более сложная логика для их различения
        # или передача типа токена отдельно.
        # Для простоты, будем использовать token_id для Coingecko и TonAPI одинаково,
        # хотя это не всегда так в реальности.

        # 1. Волатильность (CoinGecko API, исторические цены за 30 дней, σ)
        volatility_30d = 0.0
        symbol = f"UNKNOWN_{token_id[:5]}" # Значение по умолчанию для символа

        # Пытаемся получить данные с CoinGecko
        historical_prices = await self._fetch_coingecko_historical_prices(token_id, days=30)
        if historical_prices:
            std_dev = self._calculate_std_dev(historical_prices)
            # Нормализация или приведение к какому-то диапазону может потребоваться.
            # Для примера, просто используем std_dev. Если цены большие, std_dev тоже будет большой.
            # Возможно, стоит считать процентное изменение цен и волатильность на их основе.
            # Пока оставим как есть для простоты.
            average_price = sum(historical_prices) / len(historical_prices) if historical_prices else 1
            volatility_30d = (std_dev / average_price) * 100 if average_price != 0 else 0.0 # Волатильность как % от средней цены


        # 2. Ликвидность (CoinGecko, объем/капитализация)
        liquidity_score = 0.0
        market_data = await self._fetch_coingecko_market_data(token_id)
        if market_data and market_data.get("market_cap", 0) > 0:
            total_volume = market_data.get("total_volume", 0)
            market_cap = market_data.get("market_cap", 1) # Избегаем деления на ноль
            liquidity_score = (total_volume / market_cap) * 100 # Пример расчета, может быть выражен в %
            symbol = market_data.get("symbol", symbol) # Обновляем символ, если получили от CG

        # 3. Contract risk (TonAPI, holders_count — пока для Jetton, иначе 0 или mock)
        # Для TonAPI нужен адрес контракта. Если token_id - это адрес, используем его.
        # Если token_id - это ID от CoinGecko, то нам нужен способ получить адрес контракта.
        # В этой заглушке мы просто передаем token_id, предполагая, что он может быть адресом.
        contract_risk_score = 0.0 # Значение по умолчанию (высокий риск, если нет данных)
        # "Умная" заглушка: если ID похож на адрес Jetton, пытаемся получить холдеров
        # В реальном приложении нужна четкая идентификация типа token_id
        if token_id.startswith("EQ") or token_id.startswith("UQ"): # Очень упрощенная проверка на адрес TON
            holders_count = await self._fetch_tonapi_jetton_holders_count(token_id)
            if holders_count is not None and holders_count > 0:
                # Примерная логика: чем больше холдеров, тем ниже риск.
                # Шкала от 0 до 100. Макс. холдеров для 0 риска = 10000 (условно).
                # Это очень грубая оценка.
                contract_risk_score = max(0, 100 - (holders_count / 10000) * 100) if holders_count < 10000 else 0
                # Если холдеров > 10000, риск минимальный (0).
                # Если холдеров мало, риск высокий (ближе к 100).
                # Перевернем: чем больше холдеров, тем выше "оценка безопасности" (ниже риск).
                # Пусть будет от 0 до 100, где 100 - хорошо, 0 - плохо
                # Score = (holders_count / N_max_для_хорошо) * 100, capped at 100
                # Для примера, если > 5000 холдеров, то это 100.
                if holders_count > 5000:
                    contract_risk_score = 100.0
                elif holders_count > 1000:
                    contract_risk_score = 75.0
                elif holders_count > 100:
                    contract_risk_score = 50.0
                else:
                    contract_risk_score = 10.0 # Очень мало холдеров - низкая оценка
            else:
                # Не удалось получить или 0 холдеров - низкая оценка
                contract_risk_score = 5.0 # Минимальная оценка
        else:
            # Если это не адрес Jetton (например, ID CoinGecko без маппинга на адрес)
            # то contract risk будет основан на других факторах или мок
            # В данном случае, если это не Jetton-like ID, ставим средний/неопределенный риск
            print(f"[RiskV2Service] {token_id} не является Jetton адресом для оценки Contract Risk через TonAPI. Используется мок/0.")
            contract_risk_score = 50.0 # Заглушка для не-Jetton токенов


        # 4. Sentiment (временный mock: например, 50.0 до интеграции NLP)
        sentiment_score = 50.0

        # 5. Overall Risk (среднее арифметическое всех выше метрик)
        # Важно! Метрики должны быть в одной шкале, например, от 0 до 100.
        # volatility_30d - сейчас это % изменения, может быть > 100. Нужно нормализовать.
        # liquidity_score - сейчас это (объем/капа) * 100, тоже может быть большим.
        # contract_risk_score - мы сделали от 0 до 100 (где 100 - хорошо)
        # sentiment_score - 50.0 (нейтрально)

        # Для Overall Risk, предположим, что все метрики риска (где выше = хуже)
        # volatility_30d: нормализуем. Пусть макс волатильность для 100% риска = 50%.
        normalized_volatility_risk = min(100, (volatility_30d / 50.0) * 100) if volatility_30d <= 50 else 100
        if volatility_30d > 50 : normalized_volatility_risk = 100.0 # Если волатильность > 50%, риск = 100

        # liquidity_score: (объем/капа) * 100. Чем выше, тем лучше.
        # Переведем в "риск ликвидности": чем ниже score, тем выше риск.
        # Пусть идеальная ликвидность (score > 20%) = 0 риска.
        # Если score < 1%, риск = 100. Линейная интерполяция.
        normalized_liquidity_risk = 0.0
        if liquidity_score >= 20.0: # Если суточный объем > 20% от капы - хороший знак
            normalized_liquidity_risk = 0.0
        elif liquidity_score <= 1.0: # Если < 1% - очень плохо
            normalized_liquidity_risk = 100.0
        else: # от 1% до 20%
            normalized_liquidity_risk = 100.0 - ((liquidity_score - 1.0) / (20.0 - 1.0)) * 100.0

        # contract_risk_score: у нас от 0 до 100, где 100 - хорошо (мало риска).
        # Переведем в "риск контракта", где 100 - плохо.
        actual_contract_risk = 100.0 - contract_risk_score

        # sentiment_score: 50.0 (нейтрально). Пусть от 0 (очень плохо) до 100 (очень хорошо).
        # Риск сентимента = 100 - sentiment_score
        sentiment_risk = 100.0 - sentiment_score


        # Overall Risk - среднее арифметическое РИСКОВ
        # Все риски теперь от 0 (минимальный) до 100 (максимальный)
        risk_metrics = [
            normalized_volatility_risk,
            normalized_liquidity_risk,
            actual_contract_risk,
            sentiment_risk
        ]
        overall_risk_score = sum(risk_metrics) / len(risk_metrics) if risk_metrics else 0.0

        calculated_data = {
            "token_id": token_id,
            "symbol": symbol,
            "volatility_30d_percent": round(volatility_30d, 2), # Исходная волатильность в %
            "liquidity_ratio_percent": round(liquidity_score, 2), # Исходное отношение объема к капе в %
            "contract_safety_score": round(contract_risk_score, 2), # Оценка безопасности контракта (0-100, где 100 - хорошо)
            "sentiment_score": round(sentiment_score, 2), # Оценка сентимента (0-100, где 50 - нейтрально)
            "overall_risk_score": round(overall_risk_score, 2) # Общий риск (0-100, где 100 - очень высокий риск)
        }
        print(f"[RiskV2Service] Рассчитанные данные для {token_id}: {calculated_data}")
        return calculated_data

# Пример использования (для локального теста)
async def main():
    service = RiskV2Service()

    print("\n--- Тест с ID CoinGecko (например) ---")
    cg_token_id = "bitcoin"
    risk_data_cg = await service.calculate_risk(cg_token_id)
    # print(f"Риск для {cg_token_id}: {risk_data_cg}")

    print("\n--- Тест с адресом Jetton (например) ---")
    jetton_address = "EQAvlWFDxGF2lXm67y4yzC17wY79bbsE4QafajVgoVogeE7s" # Пример адреса
    risk_data_jetton = await service.calculate_risk(jetton_address)
    # print(f"Риск для {jetton_address}: {risk_data_jetton}")

    print("\n--- Тест с другим Jetton адресом ---")
    jetton_address_other = "EQBAS_ceXFAQ3EW3UAjWCK12345sE4QafajVgoVogeE7s" # Пример адреса
    risk_data_jetton_other = await service.calculate_risk(jetton_address_other)
    # print(f"Риск для {jetton_address_other}: {risk_data_jetton_other}")
    
    print("\n--- Тест с коротким ID (не Jetton) ---")
    short_id = "ton"
    risk_data_short = await service.calculate_risk(short_id)

if __name__ == "__main__":
    asyncio.run(main()) 