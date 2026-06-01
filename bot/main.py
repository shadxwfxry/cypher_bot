import sys
import logging
import asyncio
import secrets
import html
from decimal import Decimal
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import settings
from bot.database.connection import init_db
from bot.middlewares.i18n import I18nMiddleware

# Import routers
from bot.handlers.start import router as start_router
from bot.handlers.profile import router as profile_router
from bot.handlers.balance import router as balance_router
from bot.handlers.getcode import router as getcode_router

# Configure double logging to stdout and bot_errors.log file as requested
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_errors.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("bot_main")

async def start_webhook_server(bot: Bot) -> None:
    """
    Launches a lightweight aiohttp server to receive billing webhooks from the external merchant.
    Endpoint: POST /api/v1/payments/webhook
    Expects headers: X-Webhook-Secret
    """
    app = web.Application()
    
    async def handle_payment_webhook(request: web.Request) -> web.Response:
        # Check authentication header secret to ensure security
        signature = request.headers.get("X-Webhook-Secret")
        if not signature or not secrets.compare_digest(signature, settings.webhook_secret):
            logger.warning("Unauthorized invoice payment webhook hit attempt blocked.")
            return web.json_response({"status": "error", "message": "unauthorized"}, status=401)
            
        try:
            data = await request.json()
            tg_id = int(data["telegram_id"])
            amount = Decimal(str(data["amount"]))
            currency = str(data["currency"])
            usd_equiv = Decimal(str(data["usd_equivalent"]))
            method = str(data["method"])
        except Exception as e:
            logger.error(f"Malformed deposit payment webhook payload parsed: {e}")
            return web.json_response({"status": "error", "message": "malformed_payload"}, status=400)
            
        # Enforce backend-side USDT fee: deduct 5 USD if amount is between 15 and 100 USD (inclusive)
        if "USDT" in method.upper():
            if Decimal("15.00") <= usd_equiv <= Decimal("100.00"):
                logger.info(f"Applying 5 USD business fee on backend for transaction of {usd_equiv} USDT")
                usd_equiv -= Decimal("5.00")
                if usd_equiv < Decimal("0.00"):
                    usd_equiv = Decimal("0.00")
            
        # Perform transactional balance update atomically
        from bot.database.requests import get_or_create_user, process_user_deposit
        
        # Pull or register user locally
        user = await get_or_create_user(tg_id)
        
        # Credit USD equivalent amount and save transaction history atomically
        await process_user_deposit(tg_id, amount, currency, method, usd_equiv)


        
        # Instantiate translator matching user's stored language preference
        from bot.middlewares.i18n import Translator
        _ = Translator(user.language)
        
        # Compile beautiful bilingual notification alert
        success_msg = _("payment_success_msg").format(
            amount=amount,
            currency=html.escape(currency),
            usd_equiv=usd_equiv,
            method=html.escape(method)
        )
        
        try:
            await bot.send_message(chat_id=tg_id, text=success_msg, parse_mode="HTML")
            logger.info(f"Successfully processed webhook deposit of ${usd_equiv} for TG ID: {tg_id}")
        except Exception as msg_err:
            logger.error(f"Could not push TG payment alert message to user {tg_id}: {msg_err}")
            
        return web.json_response({"status": "success", "message": "balance_replenished"})

    app.router.add_post("/api/v1/payments/webhook", handle_payment_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.webhook_port)
    await site.start()
    logger.info(f"Secure payment webhook server actively listening on http://0.0.0.0:{settings.webhook_port}")

async def main():
    logger.info("Initializing Cypher.Bot...")
    
    # Initialize SQL database tables
    await init_db()
    
    # Initialize FSM storage backend (Redis in production, MemoryStorage in debug/test mode)
    if settings.debug:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.info("Using in-memory FSM storage (DEBUG mode active)")
    else:
        storage = RedisStorage.from_url(settings.redis_url)
    
    # Initialize bot client
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=storage)
    
    # Inject Custom Bilingual Localization Middleware
    dp.update.outer_middleware(I18nMiddleware())
    
    # Wire handler routers
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(balance_router)
    dp.include_router(getcode_router)
    
    # Start webserver to process external payment webhook calls
    await start_webhook_server(bot)
    
    # Flush pending queue logs and begin listening to telegram API updates
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Cypher.Bot is fully operational. Starting Aiogram long polling...")
    
    try:
        await dp.start_polling(bot)
    finally:
        from bot.api.client import api_client
        await api_client.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot execution stopped manually by keyboard interrupt.")
