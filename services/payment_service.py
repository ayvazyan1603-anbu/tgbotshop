"""
Payment Service.
"""
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession

from database import repo
from database.models import ItemType
from config import config

logger = logging.getLogger(__name__)

# ─── ВНУТРЕННИЙ БАЛАНС ───────────────────────────────────────────────────────

async def debit_balance(
    session: AsyncSession,
    user_id: int,
    amount: float,
    description: str,
) -> bool:
    user = await repo.get_user(session, user_id)
    if not user or user.balance < amount:
        return False
    await repo.update_balance(session, user_id, -amount, "spend", description)
    return True


async def credit_balance(
    session: AsyncSession,
    user_id: int,
    amount: float,
    description: str,
) -> float:
    new_balance = await repo.update_balance(
        session, user_id, amount, "deposit", description
    )
    user = await repo.get_user(session, user_id)
    if user and user.referrer_id:
        try:
            bonus = await repo.accrue_referral_bonus(session, user.referrer_id, amount)
            logger.info(f"Referral bonus {bonus} credited to {user.referrer_id}")
        except Exception as e:
            logger.error(f"Referral bonus error: {e}")
    return new_balance


# ─── ПОКУПКА ТОВАРА ──────────────────────────────────────────────────────────

async def process_purchase(
    session: AsyncSession,
    user_id: int,
    item_type: ItemType,
    item_detail: str,
    price: float,
    description: str,
    infinite_balance: bool = False,   # ← флаг из FSM (передаётся из хэндлера)
) -> Optional[int]:
    """
    Создать заказ и списать баланс.
    Если infinite_balance=True — баланс не списывается (тестовый режим).
    Возвращает order_id при успехе, None — недостаточно средств.
    """
    order = await repo.create_order(session, user_id, item_type, item_detail, price)

    if infinite_balance:
        logger.info(f"[INFINITE BALANCE] order {order.id} for user {user_id}, price {price} — not debited")
        return order.id

    success = await debit_balance(session, user_id, price, description)
    if not success:
        await repo.fail_order(session, order.id)
        return None
    return order.id


async def complete_purchase(
    session: AsyncSession,
    order_id: int,
    delivery_data: str = "",
) -> None:
    await repo.complete_order(session, order_id, delivery_data)


async def refund_purchase(
    session: AsyncSession,
    order_id: int,
    user_id: int,
    price: float,
) -> None:
    from database.models import OrderStatus, Order
    from sqlalchemy import select
    await repo.update_balance(
        session, user_id, price, "refund", f"Возврат по заказу #{order_id}"
    )
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.REFUNDED
        await session.commit()
