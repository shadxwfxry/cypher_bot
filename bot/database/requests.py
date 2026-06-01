from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import User, Purchase, Transaction
from bot.database.connection import async_session

async def get_or_create_user(
    telegram_id: int, 
    username: Optional[str] = None, 
    default_lang: str = "en"
) -> User:
    """
    Retrieves an existing user or creates a new one in the database.
    In DEBUG mode, populates the new profile with a realistic dummy purchase and transaction history.
    """
    from sqlalchemy.exc import IntegrityError
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                language=default_lang,
                balance=Decimal("0.00")
            )
            try:
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                # If running in DEBUG mode, auto-populate dummy transactional data for testing
                from bot.config import settings
                if settings.debug:
                    p1 = Purchase(telegram_id=telegram_id, product_name="💎 Premium VPN Access", amount=Decimal("15.00"))
                    p2 = Purchase(telegram_id=telegram_id, product_name="👤 USA Fullz Dossier", amount=Decimal("25.00"))
                    p3 = Purchase(telegram_id=telegram_id, product_name="📁 Scan Passport Utility", amount=Decimal("10.00"))
                    session.add_all([p1, p2, p3])
                    
                    t1 = Transaction(telegram_id=telegram_id, amount=Decimal("50.00"), currency="USDT", method="USDT_TRC20", status="completed")
                    t2 = Transaction(telegram_id=telegram_id, amount=Decimal("10.00"), currency="LTC", method="LITECOIN", status="completed")
                    session.add_all([t1, t2])
                    
                    user.balance = Decimal("50.00")
                    await session.commit()
                    await session.refresh(user)
            except IntegrityError:
                # Handle potential race conditions (e.g. parallel session created row): rollback and fetch row
                await session.rollback()
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one()
        else:
            # Sync username changes from Telegram client client-side to database record
            if username is not None and user.username != username:
                user.username = username
                await session.commit()
                await session.refresh(user)
        return user

async def get_user_by_id(telegram_id: int) -> Optional[User]:
    """Retrieves user profile data by their Telegram ID."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def get_user_by_id_for_update(telegram_id: int, session: AsyncSession) -> Optional[User]:
    """
    Acquires an exclusive row-level lock (SELECT FOR UPDATE) on a user within an active transaction.
    Used to prevent balance corruption under concurrent write access (race conditions).
    """
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).with_for_update()
    )
    return result.scalar_one_or_none()

async def update_user_language(telegram_id: int, language: str) -> None:
    """Updates user locale preference."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.language = language
            await session.commit()

async def update_user_site_login(telegram_id: int, site_login: Optional[str]) -> None:
    """Binds an authenticated marketplace website username to the Telegram profile."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.site_login = site_login
            await session.commit()

async def update_user_balance(telegram_id: int, amount: Decimal) -> Optional[Decimal]:
    """
    Updates the user balance (amount can be positive for credits or negative for debits).
    Returns the new balance value.
    """
    async with async_session() as session:
        # Prevent concurrent billing anomalies using an exclusive row lock
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user:
            user.balance += amount
            # Prevent balance from going below $0.00
            if user.balance < Decimal("0.00"):
                user.balance = Decimal("0.00")
            new_balance = user.balance
            await session.commit()
            return new_balance
        return None

async def get_user_stats(telegram_id: int) -> Tuple[int, Decimal]:
    """Returns user activity summary: (total_purchases_count, total_expenditure_usd)."""
    async with async_session() as session:
        count_query = select(func.count(Purchase.id)).where(Purchase.telegram_id == telegram_id)
        sum_query = select(func.sum(Purchase.amount)).where(Purchase.telegram_id == telegram_id)
        
        count_res = await session.execute(count_query)
        sum_res = await session.execute(sum_query)
        
        count = count_res.scalar() or 0
        total_sum = sum_res.scalar() or Decimal("0.00")
        return count, total_sum

async def add_purchase(telegram_id: int, product_name: str, amount: Decimal) -> Purchase:
    """Creates a completed purchase record log."""
    async with async_session() as session:
        purchase = Purchase(
            telegram_id=telegram_id,
            product_name=product_name,
            amount=amount
        )
        session.add(purchase)
        await session.commit()
        await session.refresh(purchase)
        return purchase

async def get_user_purchases_list(telegram_id: int, limit: int = 10) -> List[Purchase]:
    """Retrieves list of user purchases sorted by date descending."""
    async with async_session() as session:
        result = await session.execute(
            select(Purchase)
            .where(Purchase.telegram_id == telegram_id)
            .order_by(Purchase.purchased_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

async def add_transaction(
    telegram_id: int, 
    amount: Decimal, 
    currency: str, 
    method: str, 
    status: str = "completed"
) -> Transaction:
    """Creates a new deposit transaction history log."""
    async with async_session() as session:
        tx = Transaction(
            telegram_id=telegram_id,
            amount=amount,
            currency=currency,
            method=method,
            status=status
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx

async def get_user_transactions_list(telegram_id: int, limit: int = 10) -> List[Transaction]:
    """Retrieves list of deposit logs sorted by date descending."""
    async with async_session() as session:
        result = await session.execute(
            select(Transaction)
            .where(Transaction.telegram_id == telegram_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

async def get_purchases_history_3_months(telegram_id: int) -> List[Purchase]:
    """Retrieves 90-day purchase history log for document export tasks."""
    async with async_session() as session:
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        result = await session.execute(
            select(Purchase)
            .where(
                and_(
                    Purchase.telegram_id == telegram_id,
                    Purchase.purchased_at >= three_months_ago
                )
            )
            .order_by(Purchase.purchased_at.desc())
        )
        return list(result.scalars().all())

async def process_user_deposit(
    telegram_id: int, 
    amount: Decimal, 
    currency: str, 
    method: str, 
    usd_equiv: Decimal
) -> None:
    """
    Atomically credits the deposit balance and creates a transaction log.
    Both modifications are executed and committed inside a single transactional block with row locking.
    """
    async with async_session() as session:
        # Acquire dynamic row lock
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with TG ID {telegram_id} not found during balance credit.")
            
        # 1. Update user balance securely
        user.balance += usd_equiv
        if user.balance < Decimal("0.00"):
            user.balance = Decimal("0.00")
            
        # 2. Record transaction history log
        tx = Transaction(
            telegram_id=telegram_id,
            amount=amount,
            currency=currency,
            method=method,
            status="completed"
        )
        session.add(tx)
        
        # Commit atomic database transaction
        await session.commit()


