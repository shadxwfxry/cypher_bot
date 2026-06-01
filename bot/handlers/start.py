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

BANNER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "banner.png")

async def show_main_menu(message: Message, _: Callable[[str], str]) -> None:
    """Helper to send the main menu with the welcome banner."""
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
            logger.error(f"Error sending welcome photo: {e}")
            
    # Fallback to plain text if photo is missing or fails
    await message.answer(
        text=_("welcome"),
        reply_markup=get_main_menu_keyboard(_),
        parse_mode="HTML"
    )

@router.message(CommandStart())
async def start_cmd(message: Message, db_user: Any, _: Callable[[str], str]):
    """Handles the /start command."""
    await show_main_menu(message, _)

@router.callback_query(F.data == "profile:menu")
async def back_to_menu_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Handles the Back to Menu button click, returning to the main menu screen."""
    try:
        # Edit the existing photo message's caption to show main menu
        await callback.message.edit_caption(
            caption=_("welcome"),
            reply_markup=get_main_menu_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        # Fallback to delete and send a new message (e.g. if the photo message is not active)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, _)
        
    await callback.answer()

@router.callback_query(F.data == "menu:toggle_lang")
async def toggle_language_menu_callback(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    """Switches the user language preference from the main menu."""
    from bot.database.requests import update_user_language
    from bot.middlewares.i18n import Translator
    
    new_lang = "ru" if db_user.language == "en" else "en"
    await update_user_language(db_user.telegram_id, new_lang)
    
    # Update local reference and reload translator for immediate screen redraw
    db_user.language = new_lang
    new_translator = Translator(new_lang)
    
    await callback.answer(text=new_translator("lang_switched"), show_alert=True)
    
    # Redraw the main menu in place with new localized texts
    try:
        await callback.message.edit_caption(
            caption=new_translator("welcome"),
            reply_markup=get_main_menu_keyboard(new_translator),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error editing caption on language toggle: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message, new_translator)

# Generic sections display handler
@router.callback_query(F.data.startswith("menu:") & (F.data != "menu:profile") & (F.data != "menu:toggle_lang"))
async def handle_menu_sections(callback: CallbackQuery, db_user: Any, _: Callable[[str], str]):
    section = callback.data.split(":")[1]
    
    # Map section keys to translations
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
    
    # Edit the existing message or send a new one
    # Since we click from the main menu (which is a photo message), editing it directly
    # will replace the photo caption, which is perfect and extremely fluid!
    try:
        await callback.message.edit_caption(
            caption=text_content,
            reply_markup=get_back_to_main_menu_keyboard(_),
            parse_mode="HTML"
        )
    except Exception:
        # Fallback if the photo message couldn't be edited (e.g. if we were already in text mode)
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
