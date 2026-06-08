from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Optional
from bot.config import settings
from bot.services.admin_actions import is_maintenance_mode

class MaintenanceMiddleware(BaseMiddleware):
    """
    Blocks bot interactions for normal users when maintenance mode is active.
    Allows administrators (defined in settings.admin_ids) to bypass the block.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        event_user = data.get("event_from_user")
        if event_user and event_user.id in settings.admin_ids:
            return await handler(event, data)
            
        if await is_maintenance_mode():
            # Get user language preference or default to English
            db_user = data.get("db_user")
            lang = db_user.language if db_user else "en"
            
            msg = (
                "⚠️ <b>Бот временно отключен на технические работы.</b>\nПожалуйста, попробуйте зайти позже."
                if lang == "ru" else
                "⚠️ <b>The bot is temporarily closed for maintenance.</b>\nPlease try again later."
            )
            
            # Send block message depending on update type
            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(msg, parse_mode="HTML")
                elif event.callback_query:
                    await event.callback_query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
            elif isinstance(event, Message):
                await event.answer(msg, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
            return None # Block further execution
            
        return await handler(event, data)

class BanCheckMiddleware(BaseMiddleware):
    """
    Blocks bot interactions for users who are banned.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db_user = data.get("db_user")
        if db_user and db_user.is_banned:
            lang = db_user.language
            msg = (
                "❌ <b>Ваш аккаунт заблокирован администратором.</b>"
                if lang == "ru" else
                "❌ <b>Your account has been banned by the administrator.</b>"
            )
            
            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(msg, parse_mode="HTML")
                elif event.callback_query:
                    await event.callback_query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
            elif isinstance(event, Message):
                await event.answer(msg, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
            return None # Block further execution
            
        return await handler(event, data)
