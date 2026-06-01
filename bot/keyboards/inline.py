from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Callable, Optional

def get_main_menu_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Creates premium main menu keyboard.
    Highlights 'Accounts' (green) and 'Documents' (blue) sections,
    and exposes interface language switching controls directly in-place.
    """
    keyboard = [
        # Visually highlighted sections
        [InlineKeyboardButton(text=_("btn_accounts"), callback_data="menu:accounts", style="success")], # Accounts (Green)
        [InlineKeyboardButton(text=_("btn_documents"), callback_data="menu:documents", style="primary")], # Documents (Blue)
        
        # Profile & Lookup (Пробив)
        [
            InlineKeyboardButton(text=_("btn_profile"), callback_data="menu:profile"),
            InlineKeyboardButton(text=_("btn_lookup"), callback_data="menu:lookup")
        ],
        
        # Self-Reg & FULLZ sections
        [
            InlineKeyboardButton(text=_("btn_self_reg"), callback_data="menu:self_reg"),
            InlineKeyboardButton(text=_("btn_fullz"), callback_data="menu:fullz")
        ],
        
        # Rules & Updates
        [
            InlineKeyboardButton(text=_("btn_rules"), callback_data="menu:rules"),
            InlineKeyboardButton(text=_("btn_updates"), callback_data="menu:updates")
        ],
        
        # Support & Interface Language Toggle
        [
            InlineKeyboardButton(text=_("btn_support"), callback_data="menu:support"),
            InlineKeyboardButton(text=_("btn_toggle_lang"), callback_data="menu:toggle_lang")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_keyboard(_: Callable[[str], str], site_login: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Creates user 'Profile' management keyboard containing balance actions and binding options.
    """
    link_button_text = _("btn_link_account")
    link_callback = "profile:link"
    link_style = "primary"  # Blue visual highlighting to encourage user engagement
    
    if site_login:
        # If user account is linked, convert the button to a non-clickable status indicator
        link_button_text = _("btn_account_linked_active").format(login=site_login)
        link_callback = "profile:linked_status"
        link_style = None  # Neutral style when already active
 
    keyboard = [
        # Balance replenishment button - Green (success)
        [InlineKeyboardButton(text=_("btn_deposit"), callback_data="profile:deposit", style="success")],
        
        # Purchase history & Deposit logs (in one row)
        [
            InlineKeyboardButton(text=_("btn_my_purchases"), callback_data="profile:purchases"),
            InlineKeyboardButton(text=_("btn_my_deposits"), callback_data="profile:deposits")
        ],
        
        # Site account binding trigger button
        [InlineKeyboardButton(text=link_button_text, callback_data=link_callback, style=link_style)],
        
        # Return back to main menu dashboard
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="profile:menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_crypto_selection_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Creates cryptocurrency selection keyboard for payment replenishment.
    """
    keyboard = [
        [InlineKeyboardButton(text="🍬 Bitcoin", callback_data="pay:btc")],
        [InlineKeyboardButton(text="🍭 USDT TRC-20", callback_data="pay:usdt_trc20")],
        [InlineKeyboardButton(text="🍭 USDT ERC-20", callback_data="pay:usdt_erc20")],
        [InlineKeyboardButton(text="🍭 USDC ERC-20", callback_data="pay:usdc_erc20")],
        [InlineKeyboardButton(text="🍭 LTC", callback_data="pay:ltc")],
        [InlineKeyboardButton(text="🍭 ETH", callback_data="pay:eth")],
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_purchases_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Purchase history utility control keyboard (includes raw text file logs export request trigger).
    """
    keyboard = [
        [InlineKeyboardButton(text=_("btn_export_all"), callback_data="history:export_all")],
        [InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_profile_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Helper keyboard containing return button pointing back to Profile screen.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_menu"), callback_data="menu:profile")]]
    )

def get_back_to_main_menu_keyboard(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    """
    Helper keyboard containing return button pointing back to Main Menu screen.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=_("btn_menu"), callback_data="profile:menu")]]
    )

