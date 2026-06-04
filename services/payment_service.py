"""
Payment Service.
Обрабатывает:
  - Пополнение баланса (через Telegram Payments или Stars)
  - Списание с внутреннего баланса
  - Начисление реферальных бонусов
"""
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import LabeledPrice, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from database import repo
from database.models import ItemType
from config import config

logger = logging.getLogger(__name__)


# ─── ВНУТРЕННИЙ БАЛАНС ────────────────────────────────────────────────────────

async def debit_balance(
    session: AsyncSession,
    user_id: int,
    amount: float,
    description: str,
) -> bool:
    """
    Списать amount с баланса.
    Возвращает True при успехе, False — недостаточно средств.
    """
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
    """Зачислить amount на баланс. Возвращает новый баланс."""
    new_balance = await repo.update_balance(
        session, user_id, amount, "deposit", description
    )
    # Начислить реферальный бонус
    user = await repo.get_user(session, user_id)
    if user and user.referrer_id:
        try:
            bonus = await repo.accrue_referral_bonus(
                session, user.referrer_id, amount
            )
            logger.info(
                f"Referral bonus {bonus} credited to user {user.referrer_id} "
                f"from deposit of user {user_id}"
            )
        except Exception as e:
            logger.error(f"Referral bonus error: {e}")
    return new_balance


# ─── TELEGRAM INVOICE ────────────────────────────────────────────────────────

async def send_topup_invoice(
    bot: Bot,
    chat_id: int,
    amount_rub: int,
) -> None:
    """Отправить инвойс для пополнения баланса через Telegram Payments."""
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Пополнение баланса",
        description=f"Пополнение баланса на {amount_rub} руб. в цифровом маркетплейсе",
        payload=f"topup:{chat_id}:{amount_rub}",
        provider_token=config.payment_provider_token if hasattr(config, "payment_provider_token") else "",
        currency="RUB",
        prices=[LabeledPrice(label=f"Пополнение {amount_rub} руб.", amount=amount_rub * 100)],
        start_parameter="topup",
    )


# ─── ПОКУПКА ТОВАРА ──────────────────────────────────────────────────────────

async def process_purchase(
    session: AsyncSession,
    user_id: int,
    item_type: ItemType,
    item_detail: str,
    price: float,
    description: str,
) -> Optional[int]:
    """
    Создать заказ и списать баланс.
    Возвращает order_id при успехе, None — при недостаточном балансе.
    """
    # Создать заказ
    order = await repo.create_order(
        session, user_id, item_type, item_detail, price
    )
    # Попытаться списать
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
    """Завершить заказ после успешной доставки товара."""
    await repo.complete_order(session, order_id, delivery_data)


async def refund_purchase(
    session: AsyncSession,
    order_id: int,
    user_id: int,
    price: float,
) -> None:
    """Возврат средств за заказ."""
    from database.models import OrderStatus
    from sqlalchemy import select, update
    from database.models import Order
    await repo.update_balance(
        session, user_id, price, "refund", f"Возврат по заказу #{order_id}"
    )
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.REFUNDED
        await session.commit()
