import logging
import json
import html
import redis.asyncio as aioredis
from typing import Any, Callable
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from bot.database.requests import (
    get_user_stats, 
    update_user_language, 
    get_user_purchases_list, 
    get_user_transactions_list,
    update_user_site_login
)
from bot.keyboards.inline import (
    get_profile_keyboard, 
    get_purchases_keyboard, 
    get_back_to_profile_keyboard
)
from bot.api.client import api_client
from bot.config import settings

if settings.debug:
    import asyncio
    class MemoryRedisMock:
        def __init__(self):
            self.store = {}
            self.queues = {}
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value, ex=None):
            self.store[key] = str(value)
            return True
        async def incr(self, key):
            val = int(self.store.get(key, 0)) + 1
            self.store[key] = str(val)
            return val
        async def expire(self, key, seconds):
            return True
        async def rpush(self, queue_name, val):
            if queue_name not in self.queues:
                self.queues[queue_name] = []
            self.queues[queue_name].append(val)
            asyncio.create_task(self._mock_process_queue(val))
            return 1
        async def _mock_process_queue(self, payload_str):
            try:
                await asyncio.sleep(1)
                task = json.loads(payload_str)
                tg_id = task["telegram_id"]
                chat_id = task["chat_id"]
                lang = task.get("language", "en")
                from bot.worker import generate_history_file
                from aiogram import Bot
                from aiogram.types import BufferedInputFile
                from datetime import datetime
                bot = Bot(token=settings.bot_token)
                try:
                    report_bytes = await generate_history_file(tg_id)
                    if not report_bytes:
                        msg = "У вас нет истории покупок для экспорта." if lang == "ru" else "You have no purchase history to export."
                        await bot.send_message(chat_id=chat_id, text=msg)
                        return
                    doc_file = BufferedInputFile(
                        report_bytes, 
                        filename=f"cypher_history_{tg_id}_{datetime.utcnow().strftime('%Y%m%d')}.txt"
                    )
                    caption_msg = "✅ Ваша история покупок успешно сгенерирована!" if lang == "ru" else "✅ Your purchase history has been successfully generated!"
                    await bot.send_document(chat_id=chat_id, document=doc_file, caption=caption_msg)
                finally:
                    await bot.session.close()
            except Exception as e:
                import logging
                logging.getLogger("mock_queue").error(f"Error in mock worker queue: {e}")
    redis_client = MemoryRedisMock()
else:
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

logger = logging.getLogger(__name__)
router = Router(name="profile_router")

# Define FSM states for Account Linking
class LinkAccountStates(StatesGroup):
    waiting_for_hash = State()

async def send_profile_screen(message_or_query: Any, db_user: Any, _: Callable[[str], str]) -> None:
    """Helper to assemble and display the Profile card."""
    # Fetch purchases count and sum
    p_count, p_sum = await get_user_stats(db_user.telegram_id)
    
    site_login = db_user.site_login or "not linked"
    if site_login == "not linked":
        if db_user.language == "ru":
            site_login = "не привязан"
    else:
        site_login = html.escape(site_login)
        
    formatted_date = db_user.created_at.strftime("%Y-%m-%d %H:%M")
    
    profile_msg = _("profile_text").format(
        tg_id=db_user.telegram_id,
        username=html.escape(db_user.username) if db_user.username else "anonymous",
        site_login=site_login,
        reg_date=formatted_date,
        balance=db_user.balance,
        purchases_count=p_count,
        purchases_sum=p_sum
    )
    
    markup = get_profile_keyboard(_, db_user.site_login)
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            # Try to edit caption if it was a photo message
            await message_or_query.message.edit_caption(
                caption=profile_msg,
                reply_markup=markup,
                parse_mode="HTML"
            )
        except Exception:
            try:
                # Fallback to editing text if it was a text message
                await message_or_query.message.edit_text(
                    text=profile_msg,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            except Exception:
                # Fallback to answering a new message
                await message_or_query.message.answer(
                    text=profile_msg,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
    else:
        # It's a Message (from /profile command)
        await message_or_query.answer(
            text=profile_msg,
            reply_markup=markup,
            parse_mode="HTML"
        )

@router.message(Command("profile"))
@router.message(F.text.lower().in_(["profile", "профиль", "/profile"]))
async def profile_cmd(message: Message, db_user: Any, _: Callable[[str], str]):
    """Handles profile command."""
    await send_profile_screen(message, db_user, _)

@router.callback_query(F.data == "menu:profile")
async def profile_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Handles My Profile menu click."""
    await send_profile_screen(callback, db_user, _)
    await callback.answer()

@router.callback_query(F.data == "profile:lang")
async def toggle_language_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Switches the user language preference (EN <-> RU)."""
    new_lang = "ru" if db_user.language == "en" else "en"
    await update_user_language(db_user.telegram_id, new_lang)
    
    # Reload translator and updated user state
    from bot.middlewares.i18n import Translator
    new_translator = Translator(new_lang)
    db_user.language = new_lang  # update local ref for immediate redraw
    
    await callback.answer(text=new_translator("lang_switched"), show_alert=True)
    await send_profile_screen(callback, db_user, new_translator)

@router.callback_query(F.data == "profile:purchases")
async def my_purchases_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Displays last 10 purchases history with an export all button."""
    purchases = await get_user_purchases_list(db_user.telegram_id, limit=10)
    
    if not purchases:
        purchases_list_str = f"<i>{_('purchases_empty')}</i>"
    else:
        items = []
        for p in purchases:
            p_date = p.purchased_at.strftime("%Y-%m-%d %H:%M")
            items.append(_("purchases_item_format").format(
                date=p_date,
                product=html.escape(p.product_name),
                amount=p.amount
            ))
        purchases_list_str = "\n".join(items)
        
    response_text = _("purchases_title").format(purchases_list=purchases_list_str)
    
    try:
        await callback.message.edit_caption(
            caption=response_text,
            reply_markup=get_purchases_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.edit_text(
                text=response_text,
                reply_markup=get_purchases_keyboard(_),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text=response_text,
                reply_markup=get_purchases_keyboard(_),
                parse_mode="HTML"
            )
    await callback.answer()

@router.callback_query(F.data == "profile:deposits")
async def my_deposits_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Displays last 10 transactions/deposits history."""
    txs = await get_user_transactions_list(db_user.telegram_id, limit=10)
    
    if not txs:
        deposits_list_str = f"<i>{_('deposits_empty')}</i>"
    else:
        items = []
        for tx in txs:
            tx_date = tx.created_at.strftime("%Y-%m-%d %H:%M")
            # For equivalent calculation, let's assume tx.amount was recorded in crypto
            # or in dollars. In models we store the paid USD equivalent in amount,
            # or let's display the amount as USD directly.
            items.append(_("deposits_item_format").format(
                date=tx_date,
                amount=tx.amount,
                currency=html.escape(tx.currency),
                usd=tx.amount,  # Assuming transactional balance record holds USD equivalent
                method=html.escape(tx.method)
            ))
        deposits_list_str = "\n".join(items)
        
    response_text = _("deposits_title").format(deposits_list=deposits_list_str)
    
    try:
        await callback.message.edit_caption(
            caption=response_text,
            reply_markup=get_back_to_profile_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.edit_text(
                text=response_text,
                reply_markup=get_back_to_profile_keyboard(_),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text=response_text,
                reply_markup=get_back_to_profile_keyboard(_),
                parse_mode="HTML"
            )
    await callback.answer()

@router.callback_query(F.data == "profile:linked_status")
async def linked_status_alert(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Shows passive notification that user's account is already linked."""
    msg = _("link_success").format(login=db_user.site_login)
    await callback.answer(text=msg, show_alert=True)

# ----------------- FSM Account Linking Flow -----------------

@router.message(Command("link"))
@router.callback_query(F.data == "profile:link")
async def start_account_linking(event: Any, db_user: Any, _: Callable[[str], str], state: FSMContext):
    """
    Initializes the FSM linking process.
    Performs rigid safety validation checks.
    """
    # 1. Rigid Verification Check:
    # If user has purchases OR local balance > $1.0 -> BLOCK autolinking and direct to support.
    # Refetch user state and purchases within a unified SELECT FOR UPDATE transaction to prevent race conditions.
    from bot.database.connection import async_session
    from bot.database.requests import get_user_by_id_for_update
    from sqlalchemy import select, func
    from bot.database.models import Purchase
    
    async with async_session() as session:
        locked_user = await get_user_by_id_for_update(db_user.telegram_id, session)
        if not locked_user:
            if isinstance(event, CallbackQuery):
                await event.answer("User not found.")
            return
            
        db_user.balance = locked_user.balance

        # Count purchases in current transaction session
        count_res = await session.execute(
            select(func.count(Purchase.id)).where(Purchase.telegram_id == db_user.telegram_id)
        )
        p_count = count_res.scalar() or 0
        from decimal import Decimal
        if p_count > 0 or locked_user.balance > Decimal("1.00"):
            warning_msg = _("link_blocked_warn").format(
                balance=locked_user.balance, 
                support_user=settings.support_username
            )
            if isinstance(event, CallbackQuery):
                try:
                    await event.message.edit_caption(
                        caption=warning_msg,
                        reply_markup=get_back_to_profile_keyboard(_),
                        parse_mode="HTML"
                    )
                except Exception:
                    await event.message.answer(
                        text=warning_msg,
                        reply_markup=get_back_to_profile_keyboard(_),
                        parse_mode="HTML"
                    )
                await event.answer()
            else:
                await event.answer(text=warning_msg, reply_markup=get_back_to_profile_keyboard(_), parse_mode="HTML")
            return

    # 2. Clear clean slate -> enter FSM
    await state.set_state(LinkAccountStates.waiting_for_hash)
    
    prompt = _("link_prompt")
    cancel_markup = get_back_to_profile_keyboard(_)
    
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_caption(
                caption=prompt,
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
        except Exception:
            await event.message.answer(
                text=prompt,
                reply_markup=cancel_markup,
                parse_mode="HTML"
            )
        await event.answer()
    else:
        await event.answer(text=prompt, reply_markup=cancel_markup, parse_mode="HTML")

@router.message(LinkAccountStates.waiting_for_hash)
async def process_hash_input(message: Message, db_user: Any, _: Callable[[str], str], state: FSMContext):
    """Processes hash code submitted by user."""
    hash_password = message.text.strip()
    tg_id = message.from_user.id
    
    # Show typing status
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    from bot.database.connection import async_session
    from bot.database.requests import get_user_by_id_for_update
    from bot.database.models import Purchase
    from sqlalchemy import select, func
    from decimal import Decimal
    
    # PHASE 1: Quick pre-transactional check to see if user is eligible (releases DB lock immediately)
    async with async_session() as session:
        locked_user = await get_user_by_id_for_update(tg_id, session)
        if not locked_user:
            await state.clear()
            return
            
        count_res = await session.execute(
            select(func.count(Purchase.id)).where(Purchase.telegram_id == tg_id)
        )
        p_count = count_res.scalar() or 0
        
        if p_count > 0 or locked_user.balance > Decimal("1.00"):
            await state.clear()
            await message.answer(
                text=_("link_blocked_warn").format(
                    balance=locked_user.balance, 
                    support_user=settings.support_username
                ), 
                parse_mode="HTML"
            )
            return
            
    # PHASE 2: Perform network request to external API OUTSIDE the DB transaction context
    site_login = await api_client.check_hash(tg_id, hash_password)
    
    if site_login:
        # PHASE 3: Short final transaction to verify conditions again and record linking safely
        async with async_session() as session:
            locked_user = await get_user_by_id_for_update(tg_id, session)
            
            # Recheck conditions in case user managed to make a deposit during Phase 2
            count_res = await session.execute(
                select(func.count(Purchase.id)).where(Purchase.telegram_id == tg_id)
            )
            p_count = count_res.scalar() or 0
            
            if p_count > 0 or locked_user.balance > Decimal("1.00"):
                await state.clear()
                await message.answer(
                    text=_("link_blocked_warn").format(
                        balance=locked_user.balance, 
                        support_user=settings.support_username
                    ), 
                    parse_mode="HTML"
                )
                return
                
            # Perform atomic write
            locked_user.site_login = site_login
            db_user.site_login = site_login  # update local model ref
            await session.commit()
            
        await state.clear()
        
        success_msg = _("link_success").format(login=html.escape(site_login))
        await message.answer(text=success_msg, parse_mode="HTML")
        # Redisplay profile page with linked status
        await send_profile_screen(message, db_user, _)
    else:
        # Failure
        fail_msg = _("link_failed")
        await message.answer(text=fail_msg, reply_markup=get_back_to_profile_keyboard(_), parse_mode="HTML")
        # Keep them in state so they can retry or click back


# ----------------- History Background Export -----------------

@router.callback_query(F.data == "history:export_all")
async def export_all_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """
    Handles history 'Export all' button click.
    Checks user's 24h limits via Redis daily counter and queries local DB for history.
    Pushes task to Redis queue for the background worker to process sequentially.
    """
    tg_id = db_user.telegram_id
    
    # 1. Rate limit verification: max 2 exports per 24 hours per user
    # Move this to the top of the function to prevent database CPU starvation from spam queries
    from datetime import datetime
    date_str = datetime.utcnow().strftime("%Y%m%d")
    limit_key = f"export_limit:{tg_id}:{date_str}"
    
    current_count = await redis_client.incr(limit_key)
    if current_count == 1:
        await redis_client.expire(limit_key, 86400)
        
    if current_count > 2:
        await callback.answer(text=_("export_limit_exceeded"), show_alert=True)
        return
        
    # 2. Check that user actually has purchases in the last 3 months
    from bot.database.requests import get_purchases_history_3_months
    purchases = await get_purchases_history_3_months(tg_id)
    if not purchases:
        await callback.answer(text=_("export_no_purchases"), show_alert=True)
        return
        
    # 3. Compile and enqueue the export task
    task_payload = {
        "telegram_id": tg_id,
        "chat_id": callback.message.chat.id,
        "language": db_user.language
    }
    
    # Push onto sequential queue list
    await redis_client.rpush("cypher_export_queue", json.dumps(task_payload))
    
    # Notify user
    await callback.message.answer(text=_("export_queued"), parse_mode="HTML")
    await callback.answer()

