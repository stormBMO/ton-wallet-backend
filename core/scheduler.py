from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
import asyncio
import logging

# Предполагается, что RiskV2Service и TokenRisk находятся в этих путях.
# При необходимости скорректируйте импорты.
from api.risk_v2 import RiskV2Service
from models.token_risk import TokenRisk
from core.database import SessionLocal # SessionLocal теперь фабрика AsyncSession

# Настройка логирования для APScheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

scheduler = AsyncIOScheduler(timezone="UTC")

async def update_all_token_risks_job():
    """
    Периодическая задача для обновления данных о рисках для всех токенов в БД.
    """
    print("Scheduler job: Starting update_all_token_risks_job...")
    # Используем async with для управления асинхронной сессией
    async with SessionLocal() as db: # db будет AsyncSession
        try:
            stmt = select(TokenRisk.token_id)
            result = await db.execute(stmt) # Асинхронное выполнение
            token_ids_to_update = [row[0] for row in result.fetchall()] # fetchall синхронный после execute

            if not token_ids_to_update:
                print("Scheduler job: No token_ids found in token_risks table. Nothing to update.")
                return

            print(f"Scheduler job: Found {len(token_ids_to_update)} tokens to update: {token_ids_to_update}")

            for token_id in token_ids_to_update:
                print(f"Scheduler job: Attempting to update risk for token_id: {token_id}")
                try:
                    await RiskV2Service.calculate_and_save_risk(token_id, db) # Передаем AsyncSession
                    print(f"Scheduler job: Successfully updated risk for token_id: {token_id}")
                except Exception as e:
                    print(f"Scheduler job: Error updating risk for token_id {token_id}: {e}")
                await asyncio.sleep(1)

            print("Scheduler job: Finished update_all_token_risks_job successfully.")

        except Exception as e:
            print(f"Scheduler job: An error occurred during update_all_token_risks_job: {e}")
        # db.close() не нужен, т.к. `async with` сам закроет сессию
    print("Scheduler job: Database session automatically closed by 'async with'.")

def start_scheduler():
    """Запускает планировщик и добавляет задачу."""
    if not scheduler.running:
        # Добавляем задачу для выполнения каждые 5 минут
        scheduler.add_job(update_all_token_risks_job, 'interval', minutes=5, id="update_all_risks")
        scheduler.start()
        print("Scheduler started and job 'update_all_risks' added (runs every 5 minutes).")
    else:
        print("Scheduler is already running.")

async def shutdown_scheduler():
    """Корректно останавливает планировщик."""
    if scheduler.running:
        # Даем текущим задачам завершиться и затем останавливаем
        scheduler.shutdown(wait=True)
        print("Scheduler shutdown gracefully.")
    else:
        print("Scheduler is not running.")

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