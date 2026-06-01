import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from collections import defaultdict

# Prepend project root directory to sys.path to enable smooth relative packages importing when executed as standalone script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from aiogram.types import BufferedInputFile
import redis.asyncio as aioredis
from sqlalchemy import select
from bot.config import settings
from bot.database.connection import async_session
from bot.database.models import Purchase

# Configure standalone worker telemetry logs format parameters
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_errors.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("export_worker")

async def generate_history_file(telegram_id: int) -> bytes:
    """
    Retrieves purchase logs corresponding to the given Telegram user ID for the last 90 days.
    Compiles a structured report containing purchase logs ordered chronologically and grouped by day.
    """
    from datetime import timedelta
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    
    async with async_session() as session:
        result = await session.execute(
            select(Purchase)
            .where(
                Purchase.telegram_id == telegram_id,
                Purchase.purchased_at >= three_months_ago
            )
            .order_by(Purchase.purchased_at.desc())
        )
        purchases = result.scalars().all()
        
    if not purchases:
        return b""
        
    # Group purchase entries by day (YYYY-MM-DD)
    grouped_purchases = defaultdict(list)
    for p in purchases:
        day_str = p.purchased_at.strftime("%Y-%m-%d")
        grouped_purchases[day_str].append(p)
        
    # Construct document lines
    lines = [
        f"Telegram ID: {telegram_id}",
        "=" * 40,
        ""
    ]
    
    # Sort dates in descending order
    for day in sorted(grouped_purchases.keys(), reverse=True):
        lines.append(f"Purchase Date: {day}")
        lines.append("-" * 30)
        for p in grouped_purchases[day]:
            p_time = p.purchased_at.strftime("%H:%M")
            lines.append(f"[{p_time}] {p.product_name} - ${p.amount:.2f}")
        lines.append("") # Empty spacer line between days
        
    file_content = "\n".join(lines)
    return file_content.encode("utf-8")

async def worker_main():
    logger.info("Initializing Cypher.Bot Export Worker...")
    
    # Instantiate bot instance to dispatch text documents to clients
    bot = Bot(token=settings.bot_token)
    
    # Instantiate Redis queue client
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    
    logger.info("Export worker started. Listening for tasks on Redis list 'cypher_export_queue'...")
    
    try:
        while True:
            # Perform blocking read on queue (with a 5 seconds timeout to allow graceful shutdown)
            pop_res = await redis_client.brpop("cypher_export_queue", timeout=5)
            if not pop_res:
                continue
                
            _, payload_str = pop_res
            logger.info(f"Task popped from queue: {payload_str}")
            
            try:
                task = json.loads(payload_str)
                tg_id = task["telegram_id"]
                chat_id = task["chat_id"]
                lang = task.get("language", "en")
            except Exception as e:
                logger.error(f"Failed to parse task JSON: {e}")
                continue
                
            # Distributed Lock implementation to prevent concurrent file generation for the same user ID
            user_lock_key = f"export_lock:{tg_id}"
            lock_acquired = await redis_client.set(user_lock_key, "1", nx=True, ex=60)
            if not lock_acquired:
                logger.warning(f"Report for user {tg_id} is already being compiled. Task re-queued.")
                # Re-queue task to the tail of the list
                await redis_client.lpush("cypher_export_queue", payload_str)
                await asyncio.sleep(2)
                continue
                
            try:
                # Generate report byte stream
                report_bytes = await generate_history_file(tg_id)
                
                if not report_bytes:
                    logger.warning(f"No history found for Telegram ID {tg_id}")
                    msg = "У вас нет истории покупок для экспорта." if lang == "ru" else "You have no purchase history to export."
                    await bot.send_message(chat_id=chat_id, text=msg)
                    continue
                
                # Wrap byte array into buffered document container
                doc_file = BufferedInputFile(
                    report_bytes, 
                    filename=f"cypher_history_{tg_id}_{datetime.utcnow().strftime('%Y%m%d')}.txt"
                )
                
                # Deliver document file straight to user DM
                caption_msg = "✅ Ваша история покупок успешно сгенерирована!" if lang == "ru" else "✅ Your purchase history has been successfully generated!"
                await bot.send_document(
                    chat_id=chat_id,
                    document=doc_file,
                    caption=caption_msg
                )
                logger.info(f"Successfully sent history report to Telegram ID {tg_id}")
                
            except Exception as e:
                logger.error(f"Error compiling or sending history export report: {e}", exc_info=True)
                try:
                    err_msg = "❌ Произошла ошибка при экспорте истории." if lang == "ru" else "❌ An error occurred during export generation."
                    await bot.send_message(chat_id=chat_id, text=err_msg)
                except Exception:
                    pass
            finally:
                # Release user lockout token
                await redis_client.delete(user_lock_key)
                 
    except asyncio.CancelledError:
        logger.info("Worker execution cancelled. Shutting down...")
    finally:
        await bot.session.close()
        await redis_client.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(worker_main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt.")

