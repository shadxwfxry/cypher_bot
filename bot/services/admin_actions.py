import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_
from bot.database.connection import async_session
from bot.database.models import User, Purchase, Transaction, SystemSetting

logger = logging.getLogger(__name__)

async def bind_account(telegram_id: int, site_login: str) -> bool:
    """
    Decoupled business logic: manually links a Telegram account to a website account username.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.site_login = site_login
            await session.commit()
            logger.info(f"Admin bound Telegram ID {telegram_id} to site login {site_login}")
            return True
        return False

async def adjust_balance(telegram_id: int, amount: Decimal) -> Optional[Decimal]:
    """
    Decoupled business logic: adjusts user balance (can be positive or negative).
    Returns the new balance if user exists, otherwise None.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user:
            user.balance += amount
            if user.balance < Decimal("0.00"):
                user.balance = Decimal("0.00")
            new_balance = user.balance
            await session.commit()
            logger.info(f"Admin adjusted balance for TG ID {telegram_id} by {amount}. New balance: {new_balance}")
            return new_balance
        return None

async def set_ban_status(telegram_id: int, is_banned: bool) -> bool:
    """
    Decoupled business logic: bans or unbans a Telegram user.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_banned = is_banned
            await session.commit()
            logger.info(f"Admin set ban status of TG ID {telegram_id} to {is_banned}")
            return True
        return False

async def set_subscribed_status(telegram_id: int, is_subscribed: bool) -> bool:
    """
    Decoupled business logic: updates subscription newsletter status.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_subscribed = is_subscribed
            await session.commit()
            return True
        return False

async def update_user_referrer(telegram_id: int, referrer: str) -> bool:
    """
    Saves referrer param/launch parameter if user exists and does not have one set.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            if not user.referrer_param:
                user.referrer_param = referrer
                await session.commit()
                return True
        return False

async def get_period_stats(days: int) -> Dict[str, Any]:
    """
    Calculates statistics over the past N days.
    Returns counts of new users, purchases, and deposit transactions.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    async with async_session() as session:
        # 1. New users
        users_query = select(func.count(User.telegram_id)).where(User.created_at >= start_date)
        users_res = await session.execute(users_query)
        new_users = users_res.scalar() or 0
        
        # 2. Purchases count & volume
        purchases_query = select(
            func.count(Purchase.id), 
            func.sum(Purchase.amount)
        ).where(Purchase.purchased_at >= start_date)
        purchases_res = await session.execute(purchases_query)
        p_count, p_sum = purchases_res.fetchone()
        purchases_count = p_count or 0
        purchases_volume = p_sum or Decimal("0.00")
        
        # 3. Deposits count & volume
        deposits_query = select(
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        ).where(
            and_(
                Transaction.created_at >= start_date,
                Transaction.status == "completed"
            )
        )
        deposits_res = await session.execute(deposits_query)
        d_count, d_sum = deposits_res.fetchone()
        deposits_count = d_count or 0
        deposits_volume = d_sum or Decimal("0.00")
        
    return {
        "period_days": days,
        "new_users": new_users,
        "purchases_count": purchases_count,
        "purchases_volume": purchases_volume,
        "deposits_count": deposits_count,
        "deposits_volume": deposits_volume
    }

async def set_system_setting(key: str, value: str) -> None:
    """
    Dynamically saves system text/configuration values.
    """
    async with async_session() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            session.add(setting)
        await session.commit()
        logger.info(f"System setting '{key}' updated.")

async def get_system_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieves system setting values with a fallback default.
    """
    async with async_session() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else default

async def is_maintenance_mode() -> bool:
    """
    Checks if maintenance mode is currently active.
    """
    val = await get_system_setting("maintenance", "false")
    return val.lower() == "true"

async def set_maintenance_mode(is_enabled: bool) -> None:
    """
    Toggles global maintenance mode.
    """
    await set_system_setting("maintenance", "true" if is_enabled else "false")
