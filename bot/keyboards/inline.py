from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Callable, Optional

def get_main_menu_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Constructs the premium main menu keyboard.
    Highlights Accounts & Documents.
    """
    keyboard = [
        # Visually highlighted Accounts
        [InlineKeyboardButton(text=f"💎 {_('btn_accounts')} 💎", callback_data="menu:accounts")],
        # Visually highlighted Documents
        [InlineKeyboardButton(text=f"📁 {_('btn_documents')} 📁", callback_data="menu:documents")],
        # Self-Reg and FULLZ split
        [
            InlineKeyboardButton(text=_("btn_self_reg"), callback_data="menu:self_reg"),
            InlineKeyboardButton(text=_("btn_fullz"), callback_data="menu:fullz")
        ],
        # Lookup
        [InlineKeyboardButton(text=_("btn_lookup"), callback_data="menu:lookup")],
        # Profile
        [InlineKeyboardButton(text=_("btn_profile"), callback_data="menu:profile")],
        # Rules and Updates split
        [
            InlineKeyboardButton(text=_("btn_rules"), callback_data="menu:rules"),
            InlineKeyboardButton(text=_("btn_updates"), callback_data="menu:updates")
        ],
        # Support
        [InlineKeyboardButton(text=_("btn_support"), callback_data="menu:support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_keyboard(_: Callable[[str], str], site_login: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Constructs the Profile keyboard with transaction and binding controls.
    """
    link_button_text = _("btn_link_account")
    link_callback = "profile:link"
    
    if site_login:
        # If account is already linked, make it an inactive status indicator
        link_button_text = _("btn_account_linked_active").format(login=site_login)
        link_callback = "profile:linked_status"  # Leads to a status info message rather than FSM

    keyboard = [
        # Replenish Balance
        [InlineKeyboardButton(text=_("btn_deposit"), callback_data="profile:deposit")],
        # Purchases & Deposits history (Split row)
        [
            InlineKeyboardButton(text=_("btn_my_purchases"), callback_data="profile:purchases"),
            InlineKeyboardButton(text=_("btn_my_deposits"), callback_data="profile:deposits")
        ],
        # Link account
        [InlineKeyboardButton(text=link_button_text, callback_data=link_callback)],
        # Language switcher
        [InlineKeyboardButton(text=_("btn_lang"), callback_data="profile:lang")],
        # Back to main menu
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="profile:menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_crypto_selection_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Constructs the cryptocurrency selector for depositing funds.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="BTC (Bitcoin)", callback_data="pay:btc"),
            InlineKeyboardButton(text="USDT (TRC-20)", callback_data="pay:usdt")
        ],
        [
            InlineKeyboardButton(text="LTC (Litecoin)", callback_data="pay:litecoin"),
            InlineKeyboardButton(text="TRX (Tron)", callback_data="pay:tron")
        ],
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_purchases_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Keyboard displayed in the Purchases list history.
    Includes "Export all" and "Back" buttons.
    """
    keyboard = [
        [InlineKeyboardButton(text=_("btn_export_all"), callback_data="history:export_all")],
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_profile_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Simple back navigation to the user profile screen.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]]
    )

def get_back_to_main_menu_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Simple back navigation to the main menu screen.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_menu"), callback_data="profile:menu")]]
    )
