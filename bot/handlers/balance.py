import logging
import html
from typing import Any, Callable
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.keyboards.inline import get_crypto_selection_keyboard, get_back_to_profile_keyboard
from bot.api.client import api_client

logger = logging.getLogger(__name__)
router = Router(name="balance_router")

async def show_crypto_selection(message_or_query: Any, _: Callable[[str], str]) -> None:
    """Helper to display the cryptocurrency choices."""
    text = _("select_crypto")
    markup = get_crypto_selection_keyboard(_)
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_caption(
                caption=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        except Exception:
            try:
                await message_or_query.message.edit_text(
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            except Exception:
                await message_or_query.message.answer(
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
    else:
        await message_or_query.answer(text=text, reply_markup=markup, parse_mode="HTML")

@router.message(Command("balance"))
@router.message(F.text.lower().in_(["balance", "баланс", "/balance"]))
async def balance_cmd(message: Message, _: Callable[[str], str]):
    """Handles the /balance command."""
    await show_crypto_selection(message, _)

@router.callback_query(F.data == "profile:deposit")
async def deposit_callback(callback: CallbackQuery, _: Callable[[str], str]):
    """Handles click on the 'Deposit balance' button in Profile."""
    await show_crypto_selection(callback, _)
    await callback.answer()

@router.callback_query(F.data.startswith("pay:"))
async def process_payment_selection(callback: CallbackQuery, _: Callable[[str], str]):
    """
    Handles payment method selection.
    Queries external API client to get deposit address and displays it.
    Applies the custom fee policy for USDT deposits.
    """
    parts = callback.data.split(":")
    if len(parts) < 2 or not parts[1]:
        error_msg = "❌ Неверный формат платежных данных." if callback.from_user.language_code == "ru" else "❌ Invalid payment format."
        await callback.answer(error_msg)
        return
        
    cryptocurrency = parts[1].upper()
    tg_id = callback.from_user.id
    
    # Show chat action
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")
    
    # Request payment invoice from API
    invoice_data = await api_client.create_invoice(tg_id, cryptocurrency)
    
    if not invoice_data:
        # Fallback error handling
        error_text = "❌ Temporary billing offline. Please contact manager."
        if "USDT" in cryptocurrency:
            error_text = "❌ Ошибка создания платежа. Попробуйте позже."
        await callback.message.answer(text=error_text)
        await callback.answer()
        return
        
    address = invoice_data.get("address")
    
    # Rigid USDT commission warning rules:
    # 15-100 USDT -> "fee is 5 usdt"
    # 100+ USDT -> "no fee"
    if "USDT" in cryptocurrency:
        # Construct dynamic fee message block
        fee_warning = _("fee_usdt_warning")
    else:
        fee_warning = _("fee_other_warning")
        
    invoice_text = _("crypto_invoice_text").format(
        crypto=cryptocurrency,
        address=html.escape(address) if address else "",
        fee_warning=fee_warning
     )
    
    try:
        await callback.message.edit_caption(
            caption=invoice_text,
            reply_markup=get_back_to_profile_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.edit_text(
                text=invoice_text,
                reply_markup=get_back_to_profile_keyboard(_),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text=invoice_text,
                reply_markup=get_back_to_profile_keyboard(_),
                parse_mode="HTML"
            )
            
    await callback.answer()
