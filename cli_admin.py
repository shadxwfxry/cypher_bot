#!/usr/bin/env python
import os
import sys
import asyncio
import argparse
from decimal import Decimal

# Prepend project root directory to sys.path to enable smooth packages importing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.services.admin_actions import (
    bind_account,
    adjust_balance,
    set_ban_status,
    get_period_stats,
    set_system_setting,
    get_system_setting,
    set_maintenance_mode,
    is_maintenance_mode
)

async def handle_link(args):
    success = await bind_account(args.telegram_id, args.site_login)
    if success:
        print(f"✅ Successfully bound Telegram ID {args.telegram_id} to website login '{args.site_login}'.")
    else:
        print(f"❌ User with Telegram ID {args.telegram_id} not found in database.")

async def handle_balance(args):
    try:
        amount = Decimal(args.amount)
    except Exception:
        print("❌ Error: Balance adjustment amount must be a valid number.")
        return
        
    new_bal = await adjust_balance(args.telegram_id, amount)
    if new_bal is not None:
        print(f"✅ Balance updated for User {args.telegram_id}:")
        print(f"   • Adjustment: {'+' if amount > 0 else ''}{amount:.2f} USD")
        print(f"   • New Balance: ${new_bal:.2f} USD")
    else:
        print(f"❌ User with Telegram ID {args.telegram_id} not found in database.")

async def handle_ban(args):
    success = await set_ban_status(args.telegram_id, True)
    if success:
        print(f"✅ Banned Telegram user {args.telegram_id} (is_banned=True).")
    else:
        print(f"❌ User with Telegram ID {args.telegram_id} not found in database.")

async def handle_unban(args):
    success = await set_ban_status(args.telegram_id, False)
    if success:
        print(f"✅ Unbanned Telegram user {args.telegram_id} (is_banned=False).")
    else:
        print(f"❌ User with Telegram ID {args.telegram_id} not found in database.")

async def handle_stats(args):
    stats = await get_period_stats(args.days)
    print(f"📊 Statistics Report (Past {args.days} Days):")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"👥 New Users Registered:  {stats['new_users']}")
    print(f"🛍️ Purchases Volume:      {stats['purchases_count']} purchases, totaling ${stats['purchases_volume']:.2f}")
    print(f"📥 Deposits Volume:       {stats['deposits_count']} deposits, totaling ${stats['deposits_volume']:.2f}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

async def handle_maintenance(args):
    if args.status == "on":
        await set_maintenance_mode(True)
        print("✅ Maintenance Mode has been ENABLED. All regular user updates will be blocked.")
    elif args.status == "off":
        await set_maintenance_mode(False)
        print("✅ Maintenance Mode has been DISABLED. Bot is fully open to all users.")
    else:
        active = await is_maintenance_mode()
        print(f"⚙️ Maintenance Mode current status: {'ENABLED' if active else 'DISABLED'}")

async def handle_setting(args):
    if args.value:
        await set_system_setting(args.key, args.value)
        print(f"✅ System setting '{args.key}' set to: '{args.value}'")
    else:
        val = await get_system_setting(args.key)
        if val is not None:
            print(f"📝 Setting '{args.key}':\n{val}")
        else:
            print(f"❓ Setting '{args.key}' is not defined.")

def main():
    parser = argparse.ArgumentParser(
        description="Cypher.Bot CLI Admin Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # 1. Link account command
    link_parser = subparsers.add_parser("link", help="Manually bind TG ID to website user login")
    link_parser.add_argument("telegram_id", type=int, help="Telegram user ID")
    link_parser.add_argument("site_login", type=str, help="Marketplace website login")
    
    # 2. Adjust balance command
    bal_parser = subparsers.add_parser("adjust-balance", help="Modify user balance")
    bal_parser.add_argument("telegram_id", type=int, help="Telegram user ID")
    bal_parser.add_argument("amount", type=str, help="Amount to adjust (e.g. 50 or -20)")
    
    # 3. Ban command
    ban_parser = subparsers.add_parser("ban", help="Ban Telegram user")
    ban_parser.add_argument("telegram_id", type=int, help="Telegram user ID")
    
    # 4. Unban command
    unban_parser = subparsers.add_parser("unban", help="Unban Telegram user")
    unban_parser.add_argument("telegram_id", type=int, help="Telegram user ID")
    
    # 5. Stats command
    stats_parser = subparsers.add_parser("stats", help="View local system statistics")
    stats_parser.add_argument("--days", type=int, default=30, help="Statistics period in days (default: 30)")
    
    # 6. Maintenance mode command
    maint_parser = subparsers.add_parser("maintenance", help="Check or modify maintenance status")
    maint_parser.add_argument("status", choices=["on", "off", "status"], default="status", nargs="?", help="on=enable, off=disable, status=check status")
    
    # 7. System settings command
    set_parser = subparsers.add_parser("setting", help="Get or set dynamic text configurations")
    set_parser.add_argument("key", type=str, help="Configuration key (e.g., welcome_ru)")
    set_parser.add_argument("value", type=str, nargs="?", default=None, help="New text content (omit to query value)")

    args = parser.parse_args()
    
    # Map command handlers
    handlers = {
        "link": handle_link,
        "adjust-balance": handle_balance,
        "ban": handle_ban,
        "unban": handle_unban,
        "stats": handle_stats,
        "maintenance": handle_maintenance,
        "setting": handle_setting
    }
    
    # Run loop
    asyncio.run(handlers[args.command](args))

if __name__ == "__main__":
    main()
