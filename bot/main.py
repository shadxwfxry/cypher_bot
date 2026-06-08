import os
import sys
import logging
import asyncio
import secrets
import html

# Prepend project root directory to sys.path to enable smooth relative packages importing when executed as standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import settings
from bot.database.connection import init_db
from bot.middlewares.i18n import I18nMiddleware

# Import handler routers
from bot.handlers.admin import router as admin_router
from bot.handlers.start import router as start_router
from bot.handlers.profile import router as profile_router
from bot.handlers.balance import router as balance_router
from bot.handlers.getcode import router as getcode_router

# Configure logging: console (stdout) and bot_errors.log file
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
    Starts a lightweight aiohttp web server to receive billing payment webhooks.
    Endpoint: POST /api/v1/payments/webhook
    Expects authorization header: X-Webhook-Secret
    """
    app = web.Application()
    
    async def handle_payment_webhook(request: web.Request) -> web.Response:
        # Validate webhook secret signature for security
        signature = request.headers.get("X-Webhook-Secret")
        if not signature or not secrets.compare_digest(signature, settings.webhook_secret):
            logger.warning("Unauthorized payment webhook attempt blocked.")
            return web.json_response({"status": "error", "message": "unauthorized"}, status=401)
            
        try:
            data = await request.json()
            tg_id = int(data["telegram_id"])
            amount = Decimal(str(data["amount"]))
            currency = str(data["currency"])
            usd_equiv = Decimal(str(data["usd_equivalent"]))
            method = str(data["method"])
        except Exception as e:
            logger.error(f"Failed to parse payment webhook payload: {e}")
            return web.json_response({"status": "error", "message": "malformed_payload"}, status=400)
            
        # USDT Fee rule: enforce a $5 USD commission if deposit falls between $15 and $100 inclusive
        if "USDT" in method.upper():
            if Decimal("15.00") <= usd_equiv <= Decimal("100.00"):
                logger.info(f"Applying system fee of $5 USD for USDT transaction of size {usd_equiv}")
                usd_equiv -= Decimal("5.00")
                if usd_equiv < Decimal("0.00"):
                    usd_equiv = Decimal("0.00")
            
        # Process deposit database update and save transaction history atomically using row-level locking
        from bot.database.requests import get_or_create_user, process_user_deposit
        
        # Load or register user profile
        user = await get_or_create_user(tg_id)
        
        # Replenish balance and record transaction history
        await process_user_deposit(tg_id, amount, currency, method, usd_equiv)
        
        # Instantiate localized translator
        from bot.middlewares.i18n import Translator
        _ = Translator(user.language)
        
        # Compile billing replenishment notification message
        success_msg = _("payment_success_msg").format(
            amount=amount,
            currency=html.escape(currency),
            usd_equiv=usd_equiv,
            method=html.escape(method)
        )
        
        try:
            await bot.send_message(chat_id=tg_id, text=success_msg, parse_mode="HTML")
            logger.info(f"Successfully processed deposit of ${usd_equiv} for TG ID: {tg_id}")
        except Exception as msg_err:
            logger.error(f"Failed to send payment confirmation to TG ID {tg_id}: {msg_err}")
            
        return web.json_response({"status": "success", "message": "balance_replenished"})

    app.router.add_post("/api/v1/payments/webhook", handle_payment_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.webhook_port)
    await site.start()
    logger.info(f"Payment webhook server started successfully on port {settings.webhook_port}")

async def main():
    logger.info("Starting main Cypher.Bot execution pool...")
    
    # Initialize SQLAlchemy database tables if not already created
    await init_db()
    
    # Initialize FSM State Storage (Redis for production, MemoryStorage for local debug mode)
    if settings.debug:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.info("Using local in-memory FSM storage (DEBUG mode active)")
    else:
        storage = RedisStorage.from_url(settings.redis_url)
    
    # Initialize Telegram Bot API client
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=storage)
    
    # Connect i18n middleware for automatic bilingual routing
    dp.update.outer_middleware(I18nMiddleware())
    
    # Connect security middlewares (maintenance and ban enforcement)
    from bot.middlewares.security import MaintenanceMiddleware, BanCheckMiddleware
    dp.update.outer_middleware(MaintenanceMiddleware())
    dp.update.outer_middleware(BanCheckMiddleware())
    
    # Register command and callback handlers
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(balance_router)
    dp.include_router(getcode_router)
    
    # Run the dynamic payment webhook server
    await start_webhook_server(bot)
    
    # Drop pending updates and begin standard long polling loop
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Cypher.Bot is fully operational! Listening for updates...")
    
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
        logger.info("Bot execution terminated by user.")
