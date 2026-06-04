from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, String, Integer, Float, DateTime,
    ForeignKey, Boolean, Text, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ItemType(str, enum.Enum):
    STARS = "stars"
    PREMIUM = "premium"
    GIFT_REGULAR = "gift_regular"
    GIFT_SPECIAL = "gift_special"
    VPN = "vpn"
    BALANCE = "balance"


class VPNKeyStatus(str, enum.Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    referrer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    ref_earned: Mapped[float] = mapped_column(Float, default=0.0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    referrals: Mapped[list["User"]] = relationship(
        "User", foreign_keys="User.referrer_id"
    )
    referrer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[referrer_id], remote_side="User.id", overlaps="referrals"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    item_type: Mapped[str] = mapped_column(
        SAEnum(ItemType), default=ItemType.STARS
    )
    item_detail: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.PENDING
    )
    delivery_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="orders")


class VPNKey(Base):
    __tablename__ = "vpn_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(Text, unique=True)
    protocol: Mapped[str] = mapped_column(String(32), default="vless")
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(
        SAEnum(VPNKeyStatus), default=VPNKeyStatus.AVAILABLE
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Gift(Base):
    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    gift_type: Mapped[str] = mapped_column(String(32))  # "regular" | "special"
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[int] = mapped_column(Integer, default=-1)  # -1 = unlimited


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)
    tx_type: Mapped[str] = mapped_column(String(32))  # "deposit", "spend", "refund", "referral"
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
