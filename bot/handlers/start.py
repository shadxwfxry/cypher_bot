import os
import logging
from typing import Any, Callable, Optional
from decimal import Decimal
import uuid

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards.inline import get_main_menu_keyboard_async, get_back_to_main_menu_keyboard
from bot.config import settings
from bot.api.client import api_client
from bot.database.requests import add_purchase
from bot.services.admin_actions import (
    get_system_setting,
    update_user_referrer,
    adjust_balance
)

logger = logging.getLogger(__name__)
router = Router(name="start_router")

# Path to the advertising/welcome banner graphic file of the bot
BANNER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "banner.png")

async def get_welcome_text(lang: str, _: Callable[[str], str]) -> str:
    """Helper to retrieve the welcome text dynamically from DB with translation fallback."""
    welcome_key = f"welcome_{lang}"
    welcome_text = await get_system_setting(welcome_key)
    if not welcome_text:
        welcome_text = _("welcome")
    return welcome_text

async def show_main_menu(message: Message, _: Callable[[str], str], db_user: Any) -> None:
    """Helper function to deliver the main menu accompanied by the visual greeting banner."""
    welcome_text = await get_welcome_text(db_user.language, _)
    reply_markup = await get_main_menu_keyboard_async(_, db_user.language)
    
    if os.path.exists(BANNER_PATH):
        try:
            photo = FSInputFile(BANNER_PATH)
            await message.answer_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"Failed to dispatch welcome greeting banner: {e}")
            
    # Text-only fallback if the banner image resource is missing or corrupted
    await message.answer(
        text=welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

@router.message(CommandStart())
async def start_cmd(message: Message, db_user: Any, _: Callable[[str], str], command: CommandObject):
    """Handles CommandStart command /start requests and processes referrer parameter."""
    args = command.args
    if args:
        # Save referrer parameter in database if not already set
        await update_user_referrer(db_user.telegram_id, args)
        db_user.referrer_param = args
        logger.info(f"User {db_user.telegram_id} registered/started bot with referrer code: {args}")
        
    await show_main_menu(message, _, db_user)

@router.callback_query(F.data == "profile:menu")
async def back_to_menu_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Returns users back from sub-menus to the main dashboard interface."""
    welcome_text = await get_welcome_text(db_user.language, _)
    reply_markup = await get_main_menu_keyboard_async(_, db_user.language)
    
    try:
        # Edit existing caption of the banner photo for a seamless transition
        await callback.message.edit_caption(
            caption=welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception:
        # Fallback: delete obsolete message and dispatch a fresh main menu card
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, _, db_user)
        
    await callback.answer()

@router.callback_query(F.data == "menu:toggle_lang")
async def toggle_language_menu_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Switches interface language instantly directly from the main menu dashboard."""
    from bot.database.requests import update_user_language
    from bot.middlewares.i18n import Translator
    
    new_lang = "ru" if db_user.language == "en" else "en"
    await update_user_language(db_user.telegram_id, new_lang)
    
    # Update local memory cache and instantiate new translator instance for prompt rendering
    db_user.language = new_lang
    new_translator = Translator(new_lang)
    
    await callback.answer(text=new_translator("lang_switched"), show_alert=True)
    
    welcome_text = await get_welcome_text(new_lang, new_translator)
    reply_markup = await get_main_menu_keyboard_async(new_translator, new_lang)
    
    # Rerender menu inline in-place with newly updated localized dictionary keys
    try:
        await callback.message.edit_caption(
            caption=welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to update main menu caption on language toggle: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, new_translator, db_user)

# Unified message router handler for general information & dynamic product catalog sub-sections
@router.callback_query(F.data.startswith("menu:") & (F.data != "menu:profile") & (F.data != "menu:toggle_lang"))
async def handle_menu_sections(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    section = callback.data.split(":")[1]
    
    # Map callback payload triggers to bilingual dictionary keys for static categories
    section_map = {
        "rules": "rules_text",
        "updates": "updates_text",
        "support": "support_text"
    }
    
    # Check if section is a product category (accounts, documents, self_reg, fullz, lookup)
    is_product_category = section in ["accounts", "documents", "self_reg", "fullz", "lookup"]
    
    if is_product_category:
        # Retrieve products in real-time from the ExternalAPIClient
        products = await api_client.get_products(section)
        
        if products:
            # Build inline buttons for each product
            keyboard_buttons = []
            for p in products:
                button_text = f"🏷️ {p['name']} — ${p['price']:.2f}"
                keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"prod_view:{section}:{p['id']}")])
            
            # Back button
            keyboard_buttons.append([InlineKeyboardButton(text=_("btn_menu"), callback_data="profile:menu")])
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            category_names = {
                "accounts": "💎 Accounts / Аккаунты" if db_user.language == "en" else "💎 Аккаунты",
                "documents": "📁 Documents / Документы" if db_user.language == "en" else "📁 Документы",
                "self_reg": "⚙️ Self-Reg Section / Раздел Self-Reg" if db_user.language == "en" else "⚙️ Раздел Self-Reg",
                "fullz": "🪪 FULLZ Section / Раздел FULLZ" if db_user.language == "en" else "🪪 Раздел FULLZ",
                "lookup": "🔍 Lookup / Пробив" if db_user.language == "en" else "🔍 Пробив"
            }
            
            category_title = category_names.get(section, section.capitalize())
            text_content = (
                f"📂 <b>{category_title}</b>\n\n"
                "💡 <i>Select a product from the list below to view detailed specifications and purchase:</i>"
                if db_user.language == "en" else
                f"📂 <b>{category_title}</b>\n\n"
                "💡 <i>Выберите интересующий вас товар из списка ниже для просмотра характеристик и покупки:</i>"
            )
        else:
            # Fallback to default localized placeholder text if API returns empty
            trans_key = f"section_{section}"
            text_content = _(trans_key).format(support_user=settings.support_username)
            reply_markup = get_back_to_main_menu_keyboard(_)
    else:
        # Static information section
        trans_key = section_map.get(section, "welcome")
        text_content = _(trans_key).format(support_user=settings.support_username)
        reply_markup = get_back_to_main_menu_keyboard(_)
        
    try:
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception:
        # Fallback text reply if editing fails
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text=text_content,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
    await callback.answer()

# Product detail viewing handler
@router.callback_query(F.data.startswith("prod_view:"))
async def handle_product_view(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    _, category, product_id = callback.data.split(":")
    
    # Fetch all products in this category to locate the target item
    products = await api_client.get_products(category)
    product = next((p for p in products if p["id"] == product_id), None) if products else None
    
    if not product:
        err_msg = (
            "❌ Product not found or catalog was updated. Please go back."
            if db_user.language == "en" else
            "❌ Товар не найден или каталог обновился. Пожалуйста, вернитесь назад."
        )
        await callback.answer(err_msg, show_alert=True)
        return
        
    price = Decimal(str(product["price"]))
    description = product.get("desc", "No description available / Описание отсутствует")
    
    # Formulate localized detail prompt
    if db_user.language == "en":
        text_content = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"📝 <b>Description:</b>\n{description}\n\n"
            f"💵 <b>Price:</b> <code>${price:.2f}</code>\n"
            f"💳 <b>Your balance:</b> <code>${db_user.balance:.2f}</code>\n\n"
            "⚠️ <i>Please confirm your purchase. Funds will be deducted from your bot balance.</i>"
        )
        btn_buy = "💳 Confirm Purchase"
        btn_back = "🔙 Back"
    else:
        text_content = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"📝 <b>Описание:</b>\n{description}\n\n"
            f"💵 <b>Цена:</b> <code>${price:.2f}</code>\n"
            f"💳 <b>Ваш баланс:</b> <code>${db_user.balance:.2f}</code>\n\n"
            "⚠️ <i>Подтвердите покупку. Средства будут списаны с вашего баланса бота.</i>"
        )
        btn_buy = "💳 Подтвердить покупку"
        btn_back = "🔙 Назад"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_buy, callback_data=f"prod_buy:{category}:{product_id}")],
        [InlineKeyboardButton(text=btn_back, callback_data=f"menu:{category}")]
    ])
    
    try:
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text=text_content,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await callback.answer()

# Product purchasing logic
@router.callback_query(F.data.startswith("prod_buy:"))
async def handle_product_purchase(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    _, category, product_id = callback.data.split(":")
    
    # Fetch products to obtain price info
    products = await api_client.get_products(category)
    product = next((p for p in products if p["id"] == product_id), None) if products else None
    
    if not product:
        err_msg = (
            "❌ Product unavailable. Try again later."
            if db_user.language == "en" else
            "❌ Товар более недоступен для покупки."
        )
        await callback.answer(err_msg, show_alert=True)
        return
        
    price = Decimal(str(product["price"]))
    
    # 1. Verify user balance
    if db_user.balance < price:
        if db_user.language == "en":
            text_content = (
                "❌ <b>Insufficient funds!</b>\n\n"
                f"• Required amount: <code>${price:.2f}</code>\n"
                f"• Current balance: <code>${db_user.balance:.2f}</code>\n\n"
                "Please replenish your balance in your Profile before placing an order."
            )
            btn_deposit = "💳 Go to Profile (Deposit)"
            btn_back = "🔙 Back to Product"
        else:
            text_content = (
                "❌ <b>Недостаточно средств на балансе!</b>\n\n"
                f"• Стоимость товара: <code>${price:.2f}</code>\n"
                f"• Текущий баланс: <code>${db_user.balance:.2f}</code>\n\n"
                "Пожалуйста, пополните баланс в профиле перед совершением покупки."
            )
            btn_deposit = "💳 Перейти в профиль (Пополнение)"
            btn_back = "🔙 Назад к товару"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_deposit, callback_data="menu:profile")],
            [InlineKeyboardButton(text=btn_back, callback_data=f"prod_view:{category}:{product_id}")]
        ])
        
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return
        
    # 1.5 Verify account link status
    if not db_user.site_login:
        if db_user.language == "en":
            text_content = (
                "❌ <b>Linkage Required!</b>\n\n"
                "Your Telegram account must be linked to a marketplace account before making a purchase.\n\n"
                "Please go to your Profile and link your account."
            )
            btn_profile = "👤 Go to Profile"
            btn_back = "🔙 Back to Product"
        else:
            text_content = (
                "❌ <b>Требуется привязка аккаунта!</b>\n\n"
                "Ваш Telegram аккаунт должен быть привязан к аккаунту маркетплейса перед совершением покупки.\n\n"
                "Пожалуйста, перейдите в профиль для привязки аккаунта."
            )
            btn_profile = "👤 Перейти в профиль"
            btn_back = "🔙 Назад к товару"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_profile, callback_data="menu:profile")],
            [InlineKeyboardButton(text=btn_back, callback_data=f"prod_view:{category}:{product_id}")]
        ])
        
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # 2. Call website API to buy product and debit balance site-side
    buy_res = await api_client.buy_product(db_user.telegram_id, product_id)
    if not buy_res or buy_res.get("status") != "success":
        err_msg = (
            "❌ Purchase failed on the website backend. Insufficient balance or server error."
            if db_user.language == "en" else
            "❌ Ошибка покупки на стороне сайта. Недостаточный баланс или ошибка сервера."
        )
        await callback.answer(err_msg, show_alert=True)
        return
        
    # Extract product delivery details and actual price from the response
    product_item_delivery = buy_res.get("license_key", "No delivery details found.")
    actual_price = Decimal(str(buy_res.get("price", price)))

    # Deduct locally to keep DB mirrored
    new_balance = await adjust_balance(db_user.telegram_id, -actual_price)
    if new_balance is None:
        # Fallback in case of local DB error
        new_balance = db_user.balance - actual_price
        
    # Update local memory user object for immediate UI consistency
    db_user.balance = new_balance
    
    # 3. Log purchase history & mirror transaction in local database
    await add_purchase(db_user.telegram_id, product["name"], actual_price)
    await add_transaction(db_user.telegram_id, -actual_price, "USD", "purchase")
    
    if db_user.language == "en":
        text_content = (
            "🎉 <b>Purchase Successful!</b>\n\n"
            f"• <b>Product:</b> {product['name']}\n"
            f"• <b>Price:</b> <code>${actual_price:.2f}</code>\n"
            f"• <b>Remaining Balance:</b> <code>${new_balance:.2f}</code>\n\n"
            "🎁 <b>Your Order details:</b>\n"
            f"<pre>{product_item_delivery}</pre>"
        )
        btn_back = "🔙 Back to Category"
    else:
        text_content = (
            "🎉 <b>Покупка успешно совершена!</b>\n\n"
            f"• <b>Товар:</b> {product['name']}\n"
            f"• <b>Списано:</b> <code>${actual_price:.2f}</code>\n"
            f"• <b>Остаток на балансе:</b> <code>${new_balance:.2f}</code>\n\n"
            "🎁 <b>Ваши данные для доступа:</b>\n"
            f"<pre>{product_item_delivery}</pre>"
        )
        btn_back = "🔙 Назад в категорию"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_back, callback_data=f"menu:{category}")]
    ])
    
    await callback.message.edit_caption(
        caption=text_content,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
