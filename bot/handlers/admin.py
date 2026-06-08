import logging
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Callable, Any, Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from bot.config import settings
from bot.database.connection import async_session
from bot.database.models import User, Purchase, Transaction
from sqlalchemy import select, func, or_
from bot.services.admin_actions import (
    get_period_stats,
    adjust_balance,
    set_ban_status,
    is_maintenance_mode,
    set_maintenance_mode,
    set_system_setting,
    get_system_setting
)

logger = logging.getLogger(__name__)
router = Router(name="admin_router")

# Router wide protection: strictly restrict commands and callbacks to ADMIN_IDS config
router.message.filter(lambda msg: msg.from_user.id in settings.admin_ids)
router.callback_query.filter(lambda cb: cb.from_user.id in settings.admin_ids)

class AdminStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_balance_amount = State()
    waiting_for_setting_value = State()
    waiting_for_broadcast_msg = State()

def get_admin_main_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Builds the main control panel keyboard."""
    from bot.middlewares.i18n import Translator
    _ = Translator(lang)
    
    btn_toggle_lang = "English 🇬🇧" if lang == "ru" else "Русский 🇷🇺"
    
    keyboard = [
        [InlineKeyboardButton(text=_("admin_btn_stats"), callback_data="admin:stats_menu")],
        [InlineKeyboardButton(text=_("admin_btn_search"), callback_data="admin:search_user_menu")],
        [InlineKeyboardButton(text=_("admin_btn_maintenance"), callback_data="admin:maintenance_menu")],
        [InlineKeyboardButton(text=_("admin_btn_edit_texts"), callback_data="admin:edit_settings_menu")],
        [InlineKeyboardButton(text=_("admin_btn_broadcast"), callback_data="admin:broadcast_menu")],
        [
            InlineKeyboardButton(text=btn_toggle_lang, callback_data="admin:toggle_lang"),
            InlineKeyboardButton(text=_("admin_btn_close"), callback_data="admin:close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def admin_panel_cmd(message: Message, state: FSMContext, db_user: Any):
    """Entry point command to launch admin control panel."""
    await state.clear()
    from bot.middlewares.i18n import Translator
    _ = Translator(db_user.language)
    await message.answer(text=_("admin_panel_welcome"), reply_markup=get_admin_main_keyboard(db_user.language), parse_mode="HTML")

@router.callback_query(F.data == "admin:main")
async def back_to_admin_main(callback: CallbackQuery, state: FSMContext, db_user: Any):
    """Returns back to main admin menu panel."""
    await state.clear()
    from bot.middlewares.i18n import Translator
    _ = Translator(db_user.language)
    await callback.message.edit_text(text=_("admin_panel_welcome"), reply_markup=get_admin_main_keyboard(db_user.language), parse_mode="HTML")
    await callback.answer()

# --- STATISTICS SECTION ---
@router.callback_query(F.data == "admin:stats_menu")
async def stats_menu_cb(callback: CallbackQuery):
    text = (
        "📊 <b>Statistics Reports</b>\n\n"
        "Select the analytical period for which you want to query system logs (new users, purchases, deposits):"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Today / Сегодня", callback_data="admin:stats:1"),
            InlineKeyboardButton(text="7 Days / 7 дней", callback_data="admin:stats:7")
        ],
        [
            InlineKeyboardButton(text="30 Days / 30 дней", callback_data="admin:stats:30"),
            InlineKeyboardButton(text="90 Days / 90 дней", callback_data="admin:stats:90")
        ],
        [InlineKeyboardButton(text="🔙 Back / Назад", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:stats:"))
async def view_stats_cb(callback: CallbackQuery):
    days = int(callback.data.split(":")[2])
    stats = await get_period_stats(days)
    
    text = (
        f"📊 <b>System Statistics ({days} Days / {days} Дней)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>New Users / Новые пользователи:</b> <code>{stats['new_users']}</code>\n\n"
        f"🛍️ <b>Purchases / Покупки:</b>\n"
        f"• Count / Количество: <code>{stats['purchases_count']}</code>\n"
        f"• Volume / Объем: <code>${stats['purchases_volume']:.2f}</code>\n\n"
        f"📥 <b>Deposits / Пополнения:</b>\n"
        f"• Count / Количество: <code>{stats['deposits_count']}</code>\n"
        f"• Volume / Объем: <code>${stats['deposits_volume']:.2f}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>All calculations are made from the local analytical database logs.</i>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back / Назад", callback_data="admin:stats_menu")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# --- TECH WORKS (MAINTENANCE) SECTION ---
@router.callback_query(F.data == "admin:maintenance_menu")
async def maintenance_menu_cb(callback: CallbackQuery):
    is_active = await is_maintenance_mode()
    status_str = "🟢 Active (Enabled) / ВКЛЮЧЕН" if is_active else "🔴 Inactive (Disabled) / ВЫКЛЮЧЕН"
    
    text = (
        "⚙️ <b>Technical Works Management</b>\n\n"
        f"Current status: <b>{status_str}</b>\n\n"
        "When active, all bot features are blocked for regular users, displaying a warning message. "
        "Administrators can bypass this screen and use all commands normally."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Enable / Включить", callback_data="admin:maintenance:enable"),
            InlineKeyboardButton(text="🔴 Disable / Выключить", callback_data="admin:maintenance:disable")
        ],
        [InlineKeyboardButton(text="🔙 Back / Назад", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:maintenance:"))
async def toggle_maintenance_cb(callback: CallbackQuery):
    action = callback.data.split(":")[2]
    enable = (action == "enable")
    await set_maintenance_mode(enable)
    
    is_active = await is_maintenance_mode()
    status_str = "🟢 Active (Enabled) / ВКЛЮЧЕН" if is_active else "🔴 Inactive (Disabled) / ВЫКЛЮЧЕН"
    
    text = (
        "⚙️ <b>Technical Works Management</b>\n\n"
        f"Current status: <b>{status_str}</b>\n\n"
        "Settings updated successfully."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Enable / Включить", callback_data="admin:maintenance:enable"),
            InlineKeyboardButton(text="🔴 Disable / Выключить", callback_data="admin:maintenance:disable")
        ],
        [InlineKeyboardButton(text="🔙 Back / Назад", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer(text="Maintenance settings updated / Настройки сохранены", show_alert=True)

# --- EDIT TEXTS SECTION ---
@router.callback_query(F.data == "admin:edit_settings_menu")
async def edit_settings_menu_cb(callback: CallbackQuery):
    text = (
        "📝 <b>Dynamic Greetings & Button Configuration</b>\n\n"
        "You can dynamically customize welcoming texts or override standard button names. "
        "Select a system parameter key to update its value:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Start Text (RU) / Старт (RU)", callback_data="admin:setting:edit:welcome_ru"),
            InlineKeyboardButton(text="Start Text (EN) / Старт (EN)", callback_data="admin:setting:edit:welcome_en")
        ],
        [
            InlineKeyboardButton(text="Button Accounts (RU)", callback_data="admin:setting:edit:btn_accounts_ru"),
            InlineKeyboardButton(text="Button Accounts (EN)", callback_data="admin:setting:edit:btn_accounts_en")
        ],
        [
            InlineKeyboardButton(text="Button Documents (RU)", callback_data="admin:setting:edit:btn_documents_ru"),
            InlineKeyboardButton(text="Button Documents (EN)", callback_data="admin:setting:edit:btn_documents_en")
        ],
        [InlineKeyboardButton(text="🔙 Back / Назад", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:setting:edit:"))
async def edit_setting_select_cb(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[3]
    await state.update_data(target_setting_key=key)
    await state.set_state(AdminStates.waiting_for_setting_value)
    
    current_value = await get_system_setting(key, "Not set / Не установлено")
    
    text = (
        f"📝 <b>Editing System Parameter:</b> <code>{key}</code>\n\n"
        f"Current Value:\n<pre>{current_value}</pre>\n\n"
        "Please send the new text value in your next message. "
        "HTML formatting is supported. Type /cancel to abort."
    )
    
    # Simple cancel button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel / Отмена", callback_data="admin:edit_settings_menu")]
    ])
    
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext, db_user: Any):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Editing cancelled / Изменение отменено.", reply_markup=get_admin_main_keyboard(db_user.language))
        return
        
    data = await state.get_data()
    key = data["target_setting_key"]
    value = message.text
    
    await set_system_setting(key, value)
    await state.clear()
    
    await message.answer(
        text=f"✅ System setting <code>{key}</code> has been successfully updated!",
        reply_markup=get_admin_main_keyboard(db_user.language),
        parse_mode="HTML"
    )

# --- USER SEARCH & CONTROL SECTION ---
@router.callback_query(F.data == "admin:search_user_menu")
async def search_user_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_username)
    text = (
        "🔍 <b>User Search and Administration</b>\n\n"
        "Please input the target user's details. You can enter:\n"
        "• Telegram Username (e.g. <code>@john_doe</code> or <code>john_doe</code>)\n"
        "• Telegram User ID (e.g. <code>123456789</code>)\n\n"
        "<i>Send target search query as text or send /cancel to abort.</i>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel / Отмена", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

async def render_user_profile(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    """Helper to load and render user administration options."""
    async with async_session() as session:
        # Load user profile
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return "❌ User not found in database / Пользователь не найден.", None
            
        # Get purchase summaries
        purchases_query = select(
            func.count(Purchase.id),
            func.sum(Purchase.amount)
        ).where(Purchase.telegram_id == user_id)
        purchases_res = await session.execute(purchases_query)
        p_count, p_sum = purchases_res.fetchone()
        purchases_count = p_count or 0
        purchases_sum = p_sum or Decimal("0.00")
        
        # Get last purchase info
        last_purchase_query = select(Purchase).where(Purchase.telegram_id == user_id).order_by(Purchase.purchased_at.desc()).limit(1)
        last_purchase_res = await session.execute(last_purchase_query)
        last_purchase = last_purchase_res.scalar_one_or_none()
        
    last_p_str = "None / Нет покупок"
    if last_purchase:
        last_p_str = f"🛍️ {last_purchase.product_name} - ${last_purchase.amount:.2f} ({last_purchase.purchased_at.strftime('%Y-%m-%d %H:%M')})"
        
    ban_status = "🚫 BANNED / ЗАБАНЕН" if user.is_banned else "✅ Active / Активен"
    sub_status = "✅ Subscribed / Подписан" if user.is_subscribed else "❌ Not Subscribed / Отписан"
    ref_param = user.referrer_param if user.referrer_param else "Direct (None) / Нет"
    site_log = user.site_login if user.site_login else "Not linked / Не привязан"
    
    text = (
        f"👤 <b>User Control Profile:</b> @{user.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>TG ID:</b> <code>{user.telegram_id}</code>\n"
        f"• <b>Site Account Login:</b> <code>{site_log}</code>\n"
        f"• <b>Status:</b> <b>{ban_status}</b>\n"
        f"• <b>Broadcast:</b> {sub_status}\n"
        f"• <b>Ref parameter:</b> <code>{ref_param}</code>\n"
        f"• <b>Register Date:</b> {user.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"💳 <b>Current Balance:</b> <code>${user.balance:.2f}</code>\n"
        f"🛍️ <b>Total Purchases:</b> <code>{purchases_count}</code> (<code>${purchases_sum:.2f}</code>)\n\n"
        f"📍 <b>Last purchase / Последняя покупка:</b>\n"
        f"<i>{last_p_str}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    ban_btn_text = "🟢 Unban / Разбанить" if user.is_banned else "🔴 Ban User / Забанить"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Adjust Balance / Изменить баланс", callback_data=f"admin:usr:balance:{user.telegram_id}"),
            InlineKeyboardButton(text=ban_btn_text, callback_data=f"admin:usr:ban_toggle:{user.telegram_id}")
        ],
        [InlineKeyboardButton(text="🔙 Search Again / Искать заново", callback_data="admin:search_user_menu")],
        [InlineKeyboardButton(text="🔙 Admin Panel / В меню", callback_data="admin:main")]
    ])
    
    return text, keyboard

@router.message(AdminStates.waiting_for_username)
async def process_user_search(message: Message, state: FSMContext, db_user: Any):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Search cancelled.", reply_markup=get_admin_main_keyboard(db_user.language))
        return
        
    query = message.text.strip().replace("@", "")
    
    # Try searching by username or telegram id
    async with async_session() as session:
        if query.isdigit():
            user_id = int(query)
            result = await session.execute(select(User).where(User.telegram_id == user_id))
        else:
            result = await session.execute(
                select(User).where(func.lower(User.username) == query.lower())
            )
        target_user = result.scalar_one_or_none()
        
    if not target_user:
        await message.answer(
            text="❌ User not found in local database. Check username/ID and try again, or type /cancel.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel / Отмена", callback_data="admin:main")]
            ])
        )
        return
        
    await state.clear()
    profile_text, keyboard = await render_user_profile(target_user.telegram_id)
    await message.answer(text=profile_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:usr:ban_toggle:"))
async def toggle_user_ban_cb(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[3])
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            # Toggle ban status
            user.is_banned = not user.is_banned
            new_status = user.is_banned
            await session.commit()
            logger.info(f"Admin toggled ban for user {tg_id} to {new_status}")
            
    # Rerender profile info inline
    profile_text, keyboard = await render_user_profile(tg_id)
    await callback.message.edit_text(text=profile_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer(text="Ban status updated / Статус бана изменен", show_alert=True)

@router.callback_query(F.data.startswith("admin:usr:balance:"))
async def adjust_balance_prompt_cb(callback: CallbackQuery, state: FSMContext):
    tg_id = int(callback.data.split(":")[3])
    await state.update_data(target_user_id=tg_id)
    await state.set_state(AdminStates.waiting_for_balance_amount)
    
    text = (
        f"💳 <b>Balance Adjustment for User</b>: <code>{tg_id}</code>\n\n"
        "Please send the amount to add or subtract from user's balance.\n"
        "• To add funds, send positive number: e.g. <code>25</code> or <code>10.50</code>\n"
        "• To deduct funds, send negative prefix: e.g. <code>-15</code> or <code>-5.00</code>\n\n"
        "<i>Send value as message or type /cancel to abort.</i>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel / Отмена", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_balance_amount)
async def process_balance_adjustment(message: Message, state: FSMContext, db_user: Any):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Balance adjustment cancelled.", reply_markup=get_admin_main_keyboard(db_user.language))
        return
        
    try:
        amount = Decimal(message.text.strip())
    except Exception:
        await message.answer("❌ Invalid numerical format. Send a number (e.g. 10 or -15) or type /cancel.")
        return
        
    data = await state.get_data()
    tg_id = data["target_user_id"]
    
    new_bal = await adjust_balance(tg_id, amount)
    await state.clear()
    
    if new_bal is not None:
        text = (
            f"✅ Balance successfully updated!\n\n"
            f"• Target User: <code>{tg_id}</code>\n"
            f"• Adjustment: <code>{'+' if amount > 0 else ''}{amount:.2f} USD</code>\n"
            f"• New Balance: <code>${new_bal:.2f} USD</code>"
        )
    else:
        text = "❌ Failed to update balance. User not found / Ошибка выполнения."
        
    await message.answer(text=text, reply_markup=get_admin_main_keyboard(db_user.language), parse_mode="HTML")

# --- BULK NEWSLETTER BROADCAST SECTION ---
@router.callback_query(F.data == "admin:broadcast_menu")
async def broadcast_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    
    # Get total count of subscribed users
    async with async_session() as session:
        res = await session.execute(
            select(func.count(User.telegram_id)).where(User.is_subscribed == True)
        )
        sub_count = res.scalar() or 0
        
    text = (
        "📢 <b>Bulk Newsletter Broadcaster</b>\n\n"
        f"Current Subscribed Audience: <b>{sub_count} users</b>\n\n"
        "Please send the message you wish to broadcast to all subscribed users. "
        "Your message can include formatted text, photo/media attachments, and hyperlinks. "
        "Type /cancel to abort."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel / Отмена", callback_data="admin:main")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_msg)
async def process_broadcast_message(message: Message, state: FSMContext, db_user: Any):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Broadcast cancelled.", reply_markup=get_admin_main_keyboard(db_user.language))
        return
        
    # Save the message parameters in state data
    await state.update_data(
        broadcast_text=message.html_text or message.text,
        broadcast_photo=message.photo[-1].file_id if message.photo else None
    )
    
    async with async_session() as session:
        res = await session.execute(
            select(func.count(User.telegram_id)).where(User.is_subscribed == True)
        )
        sub_count = res.scalar() or 0
        
    text = (
        "📢 <b>Confirm Newsletter Release</b>\n\n"
        f"You are about to send a newsletter to <b>{sub_count} users</b>.\n\n"
        "Please confirm to proceed. Sending starts immediately and will bypass flood blocks using asyncio delays."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, Release / Да, запустить", callback_data="admin:broadcast:confirm"),
            InlineKeyboardButton(text="❌ Cancel / Отмена", callback_data="admin:main")
        ]
    ])
    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "admin:broadcast:confirm")
async def confirm_broadcast_cb(callback: CallbackQuery, state: FSMContext, bot: Bot, db_user: Any):
    state_data = await state.get_data()
    text = state_data.get("broadcast_text")
    photo_id = state_data.get("broadcast_photo")
    
    if not text:
        await callback.answer("Error: Message empty / Ошибка: пустое сообщение", show_alert=True)
        await state.clear()
        return
        
    await state.clear()
    
    # Query all subscribed user IDs
    async with async_session() as session:
        result = await session.execute(
            select(User.telegram_id).where(User.is_subscribed == True)
        )
        recipient_ids = [row[0] for row in result.fetchall()]
        
    total_recipients = len(recipient_ids)
    if total_recipients == 0:
        await callback.message.edit_text(
            text="❌ No subscribed users found. Broadcast aborted.",
            reply_markup=get_admin_main_keyboard(db_user.language)
        )
        return
        
    await callback.message.edit_text(
        text=f"⏳ <b>Broadcast started...</b>\nTarget recipients: {total_recipients} users.\nYou will receive a summary upon completion.",
        parse_mode="HTML"
    )
    
    # Start asynchronous background task for broadcasting to avoid blocking bot execution loop
    asyncio.create_task(run_broadcast_loop(bot, callback.from_user.id, recipient_ids, text, photo_id, db_user.language))
    await callback.answer()

async def run_broadcast_loop(bot: Bot, admin_id: int, recipient_ids: list[int], text: str, photo_id: Optional[str], admin_lang: str = "en"):
    """Background worker loop to transmit message with flood control delay."""
    success_count = 0
    fail_count = 0
    
    for user_id in recipient_ids:
        try:
            if photo_id:
                await bot.send_photo(chat_id=user_id, photo=photo_id, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to deliver broadcast message to user {user_id}: {e}")
            fail_count += 1
            
        # Standard anti-flood throttling delay (approx. 20 messages per second limit)
        await asyncio.sleep(0.05)
        
    summary_text = (
        "📢 <b>Newsletter Broadcast Finished!</b>\n\n"
        f"• Total Audience: <code>{len(recipient_ids)}</code>\n"
        f"• Successfully sent: <code>{success_count}</code>\n"
        f"• Failed / Blocked: <code>{fail_count}</code>"
    )
    
    try:
        await bot.send_message(chat_id=admin_id, text=summary_text, reply_markup=get_admin_main_keyboard(admin_lang), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to deliver final broadcast report to admin {admin_id}: {e}")

# --- CLOSE PANEL TRIGGER ---
@router.callback_query(F.data == "admin:close")
async def close_admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer(text="Admin panel closed / Админ-панель закрыта")

@router.callback_query(F.data == "admin:toggle_lang")
async def toggle_admin_language(callback: CallbackQuery, db_user: Any):
    from bot.database.requests import update_user_language
    from bot.middlewares.i18n import Translator
    
    new_lang = "ru" if db_user.language == "en" else "en"
    await update_user_language(db_user.telegram_id, new_lang)
    
    db_user.language = new_lang
    new_translator = Translator(new_lang)
    
    await callback.answer(text=new_translator("lang_switched"), show_alert=True)
    
    text = new_translator("admin_panel_welcome")
    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_main_keyboard(new_lang),
        parse_mode="HTML"
    )
