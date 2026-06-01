from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

class User(Base):
    """Telegram user database model."""
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")  # Language locale: 'ru' or 'en'
    site_login: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)  # Linked site login/username
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))  # Balance in USD
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # One-to-many relationships
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Purchase(Base):
    """User purchase log model."""
    __tablename__ = "purchases"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="RESTRICT"))
    product_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # Purchase price in USD
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="purchases")

class Transaction(Base):
    """Financial transactions (deposits) log model."""
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # Replenishment amount
    currency: Mapped[str] = mapped_column(String(50))        # Cryptocurrency token (e.g. BTC, USDT)
    method: Mapped[str] = mapped_column(String(50))          # Payment method network (e.g. USDT_TRC20)
    status: Mapped[str] = mapped_column(String(50), default="completed")  # Transaction status: completed, pending
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="transactions")

