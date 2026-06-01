import logging
import html
from typing import Any, Callable
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bot.api.client import api_client
from bot.keyboards.inline import get_back_to_profile_keyboard

logger = logging.getLogger(__name__)
router = Router(name="getcode_router")

@router.message(Command("getcode"))
@router.message(F.text.lower().in_(["getcode", "код", "2fa", "/getcode"]))
async def get_2fa_code_handler(message: Message, db_user: Any, _: Callable[[str], str]):
    """
    Handles real-time 2FA generation.
    Checks if account is linked. If not, blocks request and alerts.
    If linked, requests 6-digit code via secure external API.
    """
    # Verify account is linked
    if not db_user.site_login:
        warn_msg = _("twofa_not_linked")
        await message.answer(
            text=warn_msg, 
            reply_markup=get_back_to_profile_keyboard(_),
            parse_mode="HTML"
        )
        return
        
    # User is linked -> show typing action while hitting API
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    code = await api_client.get_2fa_code(db_user.telegram_id)
    
    if code:
        code_msg = _("twofa_code_msg").format(code=html.escape(str(code)))
        await message.answer(text=code_msg, parse_mode="HTML")
    else:
        fail_msg = _("twofa_failed")
        await message.answer(
            text=fail_msg,
            reply_markup=get_back_to_profile_keyboard(_),
            parse_mode="HTML"
        )
