from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Order, VPNKey, Gift, Transaction, OrderStatus, ItemType, VPNKeyStatus
from config import config


# ─── USER REPO ───────────────────────────────────────────────────────────────

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str],
    full_name: str,
    referrer_id: Optional[int] = None,
) -> tuple[User, bool]:
    user = await get_user(session, user_id)
    if user:
        # Update username/name if changed
        user.username = username
        user.full_name = full_name
        await session.commit()
        return user, False

    # Validate referrer
    valid_referrer = None
    if referrer_id and referrer_id != user_id:
        ref = await get_user(session, referrer_id)
        if ref:
            valid_referrer = referrer_id

    user = User(
        id=user_id,
        username=username,
        full_name=full_name,
        balance=0.0,
        referrer_id=valid_referrer,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True


async def update_balance(
    session: AsyncSession,
    user_id: int,
    amount: float,
    tx_type: str,
    description: str = "",
) -> float:
    """Add or subtract balance. Returns new balance."""
    user = await get_user(session, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    user.balance = round(user.balance + amount, 2)
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        tx_type=tx_type,
        description=description,
    )
    session.add(tx)
    await session.commit()
    return user.balance


async def accrue_referral_bonus(
    session: AsyncSession,
    referrer_id: int,
    deposit_amount: float,
) -> float:
    """Credit referral bonus to referrer. Returns bonus amount."""
    bonus = round(deposit_amount * config.referral_percent / 100, 2)
    referrer = await get_user(session, referrer_id)
    if not referrer:
        return 0.0
    referrer.balance = round(referrer.balance + bonus, 2)
    referrer.ref_earned = round(referrer.ref_earned + bonus, 2)
    tx = Transaction(
        user_id=referrer_id,
        amount=bonus,
        tx_type="referral",
        description=f"Реферальный бонус {config.referral_percent}%",
    )
    session.add(tx)
    await session.commit()
    return bonus


async def get_referral_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count()).where(User.referrer_id == user_id)
    )
    return result.scalar_one()


async def get_user_orders(session: AsyncSession, user_id: int) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


# ─── ORDER REPO ──────────────────────────────────────────────────────────────

async def create_order(
    session: AsyncSession,
    user_id: int,
    item_type: ItemType,
    item_detail: str,
    price: float,
) -> Order:
    order = Order(
        user_id=user_id,
        item_type=item_type,
        item_detail=item_detail,
        price=price,
        status=OrderStatus.PENDING,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def complete_order(
    session: AsyncSession,
    order_id: int,
    delivery_data: str = "",
) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    order.status = OrderStatus.COMPLETED
    order.delivery_data = delivery_data
    await session.commit()
    return order


async def fail_order(session: AsyncSession, order_id: int) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    order.status = OrderStatus.FAILED
    await session.commit()
    return order


# ─── VPN KEY REPO ─────────────────────────────────────────────────────────────

async def get_available_vpn_key(
    session: AsyncSession, duration_days: int
) -> Optional[VPNKey]:
    result = await session.execute(
        select(VPNKey)
        .where(
            VPNKey.status == VPNKeyStatus.AVAILABLE,
            VPNKey.duration_days == duration_days,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def assign_vpn_key(
    session: AsyncSession, key_id: int, user_id: int
) -> VPNKey:
    result = await session.execute(select(VPNKey).where(VPNKey.id == key_id))
    vpn_key = result.scalar_one()
    vpn_key.status = VPNKeyStatus.SOLD
    vpn_key.user_id = user_id
    vpn_key.expires_at = datetime.utcnow() + timedelta(days=vpn_key.duration_days)
    await session.commit()
    return vpn_key


async def add_vpn_key(
    session: AsyncSession,
    key: str,
    protocol: str,
    duration_days: int,
) -> VPNKey:
    vpn_key = VPNKey(
        key=key,
        protocol=protocol,
        duration_days=duration_days,
        status=VPNKeyStatus.AVAILABLE,
    )
    session.add(vpn_key)
    await session.commit()
    await session.refresh(vpn_key)
    return vpn_key


# ─── GIFT REPO ───────────────────────────────────────────────────────────────

async def get_gifts(session: AsyncSession, gift_type: str) -> list[Gift]:
    result = await session.execute(
        select(Gift)
        .where(Gift.gift_type == gift_type, Gift.is_available == True)
        .order_by(Gift.id)
    )
    return list(result.scalars().all())


async def get_gift(session: AsyncSession, gift_id: int) -> Optional[Gift]:
    result = await session.execute(select(Gift).where(Gift.id == gift_id))
    return result.scalar_one_or_none()


# ─── STATS ───────────────────────────────────────────────────────────────────

async def get_total_orders_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .where(Order.user_id == user_id, Order.status == OrderStatus.COMPLETED)
    )
    return result.scalar_one()
