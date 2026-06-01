import os
import logging
from typing import Any, Callable
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from bot.keyboards.inline import get_main_menu_keyboard, get_back_to_main_menu_keyboard
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name="start_router")

# Path to the advertising/welcome banner graphic file of the bot
BANNER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "banner.png")

async def show_main_menu(message: Message, _: Callable[[str], str]) -> None:
    """Helper function to deliver the main menu accompanied by the visual greeting banner."""
    if os.path.exists(BANNER_PATH):
        try:
            photo = FSInputFile(BANNER_PATH)
            await message.answer_photo(
                photo=photo,
                caption=_("welcome"),
                reply_markup=get_main_menu_keyboard(_),
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"Failed to dispatch welcome greeting banner: {e}")
            
    # Text-only fallback if the banner image resource is missing or corrupted
    await message.answer(
        text=_("welcome"),
        reply_markup=get_main_menu_keyboard(_),
        parse_mode="HTML"
    )

@router.message(CommandStart())
async def start_cmd(message: Message, db_user: Any, _: Callable[[str], str]):
    """Handles CommandStart command /start requests."""
    await show_main_menu(message, _)

@router.callback_query(F.data == "profile:menu")
async def back_to_menu_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Returns users back from sub-menus to the main dashboard interface."""
    try:
        # Edit existing caption of the banner photo for a seamless transition
        await callback.message.edit_caption(
            caption=_("welcome"),
            reply_markup=get_main_menu_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        # Fallback: delete obsolete message and dispatch a fresh main menu card
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, _)
        
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
    
    # Rerender menu inline in-place with newly updated localized dictionary keys
    try:
        await callback.message.edit_caption(
            caption=new_translator("welcome"),
            reply_markup=get_main_menu_keyboard(new_translator),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to update main menu caption on language toggle: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, new_translator)

# Unified message router handler for general information sub-sections of the main menu
@router.callback_query(F.data.startswith("menu:") & (F.data != "menu:profile") & (F.data != "menu:toggle_lang"))
async def handle_menu_sections(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    section = callback.data.split(":")[1]
    
    # Map callback payload triggers to bilingual dictionary keys
    section_map = {
        "accounts": "section_accounts",
        "documents": "section_documents",
        "self_reg": "section_self_reg",
        "fullz": "section_fullz",
        "lookup": "section_lookup",
        "rules": "rules_text",
        "updates": "updates_text",
        "support": "support_text"
    }
    
    trans_key = section_map.get(section, "welcome")
    text_content = _(trans_key).format(support_user=settings.support_username)
    
    # Edit the active image caption to provide a flicker-free visual transition.
    # Editing the existing photo message avoids client screen jumps.
    try:
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=get_back_to_main_menu_keyboard(_),
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
            reply_markup=get_back_to_main_menu_keyboard(_),
            parse_mode="HTML"
        )
        
    await callback.answer()

