import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from models.token_risk import TokenRisk
from services.risk_v2_service import RiskV2Service
# Используем SessionLocal из core.database и даем ему псевдоним AsyncSessionLocal
# для совместимости с ожиданиями в этом файле.
from core.database import SessionLocal as AsyncSessionLocal 

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Базовая конфигурация логгера

async def update_all_token_risks_job():
    """
    Фоновая задача для периодического обновления всех метрик риска токенов.
    1. Получает все token_id из таблицы token_risks.
    2. Для каждого token_id вызывает RiskV2Service для расчета новых метрик.
    3. Сохраняет обновленные данные обратно в БД.
    """
    logger.info("[SchedulerJob] Запуск задачи: update_all_token_risks_job")
    risk_service = RiskV2Service()
    
    # Используем AsyncSessionLocal (псевдоним для SessionLocal) для создания сессии внутри задачи
    async with AsyncSessionLocal() as session:
        try:
            # 1. Получить список всех token_id из таблицы
            stmt_get_ids = select(TokenRisk.token_id)
            result_ids = await session.execute(stmt_get_ids)
            token_ids = result_ids.scalars().all()

            if not token_ids:
                logger.info("[SchedulerJob] В таблице token_risks нет токенов для обновления.")
                return

            logger.info(f"[SchedulerJob] Найдено {len(token_ids)} токенов для обновления: {token_ids}")
            successful_updates = 0
            failed_updates = 0

            for token_id in token_ids:
                try:
                    logger.debug(f"[SchedulerJob] Обработка token_id: {token_id}")
                    
                    # 2. Рассчитать данные с помощью сервиса
                    # Сервис возвращает словарь, например:
                    # {
                    #     "token_id": token_id,
                    #     "symbol": symbol,
                    #     "volatility_30d_percent": round(volatility_30d, 2),
                    #     "liquidity_ratio_percent": round(liquidity_score, 2),
                    #     "contract_safety_score": round(contract_risk_score, 2), # 0-100, 100=good
                    #     "sentiment_score": round(sentiment_score, 2), # 0-100, 50=neutral, 100=good
                    #     "overall_risk_score": round(overall_risk_score, 2) # 0-100, 100=high risk
                    # }
                    calculated_data = await risk_service.calculate_risk(token_id) 
                    
                    # 3. Найти и обновить запись в БД
                    stmt_select_token = select(TokenRisk).where(TokenRisk.token_id == token_id)
                    res_token = await session.execute(stmt_select_token)
                    token_risk_entry = res_token.scalars().first()

                    if token_risk_entry:
                        token_risk_entry.symbol = calculated_data["symbol"]
                        token_risk_entry.volatility_30d = calculated_data["volatility_30d_percent"]
                        token_risk_entry.liquidity_score = calculated_data["liquidity_ratio_percent"] # Higher is better
                        token_risk_entry.sentiment_score = calculated_data["sentiment_score"] # Higher is better
                        # contract_safety_score (100=good) -> contract_risk_score (100=bad)
                        token_risk_entry.contract_risk_score = 100.0 - calculated_data["contract_safety_score"]
                        token_risk_entry.overall_risk_score = calculated_data["overall_risk_score"] # Higher is riskier
                        # updated_at обновится автоматически через onupdate=func.now() в модели
                        
                        logger.debug(f"[SchedulerJob] Данные для {token_id} обновлены в сессии.")
                        successful_updates += 1
                    else:
                        # Эта ситуация не должна возникать, если мы берем token_id из той же таблицы,
                        # которую обновляем, и не удаляем записи между выборкой и обновлением.
                        logger.warning(f"[SchedulerJob] Token ID {token_id} был выбран из БД, но не найден для обновления. Пропускается.")
                        failed_updates += 1
                        continue
                
                except Exception as e:
                    logger.error(f"[SchedulerJob] Ошибка при обработке или расчете риска для токена {token_id}: {e}", exc_info=True)
                    failed_updates += 1
                    # Не откатываем здесь, т.к. коммит в конце. Ошибка для одного токена не должна прерывать другие.

            if successful_updates > 0:
                await session.commit()
                logger.info(f"[SchedulerJob] Коммит обновлений для {successful_updates} токенов. Ошибок/пропущено: {failed_updates}.")
            else:
                logger.info(f"[SchedulerJob] Нет успешных обновлений для коммита. Ошибок/пропущено: {failed_updates}.")

        except Exception as e:
            # В случае крупной ошибки (например, проблема с БД при первоначальном запросе)
            await session.rollback() 
            logger.error(f"[SchedulerJob] Критическая ошибка во время выполнения задачи обновления токенов: {e}", exc_info=True)
        # Сессия автоматически закроется благодаря `async with AsyncSessionLocal() as session:`

# Создание экземпляра планировщика
scheduler = AsyncIOScheduler(timezone="UTC") # Рекомендуется указывать таймзону

# Добавление задачи в планировщик
# Будет запускаться каждые 5 минут
scheduler.add_job(
    update_all_token_risks_job, 
    'interval', 
    minutes=5, 
    id="update_all_risks_job", 
    replace_existing=True # Заменять существующую задачу с таким же ID, если она есть
)

# Функции для управления планировщиком из main.py
def start_scheduler():
    if not scheduler.running:
        try:
            scheduler.start()
            logger.info("Планировщик APScheduler запущен.")
        except Exception as e:
            logger.error(f"Ошибка при запуске APScheduler: {e}", exc_info=True)


def shutdown_scheduler():
    if scheduler.running:
        try:
            scheduler.shutdown() # graceful shutdown
            logger.info("Планировщик APScheduler остановлен.")
        except Exception as e:
            logger.error(f"Ошибка при остановке APScheduler: {e}", exc_info=True)

# Пример использования (не для FastAPI, а для отдельного запуска, если нужно)
# async def main():
#     start_scheduler()
#     try:
#         while True:
#             await asyncio.sleep(1)
#     except (KeyboardInterrupt, SystemExit):
#         await shutdown_scheduler()

# if __name__ == "__main__":
#     asyncio.run(main()) 