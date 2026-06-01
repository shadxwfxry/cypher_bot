from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from typing import Callable, Dict, Any, Awaitable, Optional
from bot.database.requests import get_or_create_user

class Translator:
    def __init__(self, lang: str):
        self.lang = lang if lang in ["ru", "en"] else "en"

    def get(self, key: str, default: Optional[str] = None) -> str:
        from bot.locales.translation import TRANSLATIONS
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["en"]).get(key, default or key)
    
    def __call__(self, key: str, default: Optional[str] = None) -> str:
        return self.get(key, default)

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        event_user: Optional[TgUser] = data.get("event_from_user")
        if not event_user:
            return await handler(event, data)
        
        # Load user from DB (or create with default language matching client if valid, otherwise en)
        default_lang = "en"
        if event_user.language_code and event_user.language_code.lower() in ["ru", "en"]:
            default_lang = event_user.language_code.lower()
            
        user = await get_or_create_user(
            telegram_id=event_user.id,
            username=event_user.username or f"user_{event_user.id % 10000}",
            default_lang=default_lang
        )
        
        # Instantiate translator with user database language
        translator = Translator(user.language)
        
        # Inject into handler arguments
        data["_"] = translator
        data["db_user"] = user
        
        return await handler(event, data)
