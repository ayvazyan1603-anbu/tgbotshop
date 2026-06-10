"""
Пополнение баланса через Telegram Stars (XTR).
Подключи этот роутер в handlers/__init__.py.
"""
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment,
)
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from database import repo
from services.payment_service import credit_balance
from keyboards.inline import main_menu_kb

router = Router()

# Курс: сколько рублей даётся за 1 звезду
RUB_PER_STAR = 1.8


@router.callback_query(F.data.startswith("topup_stars:"))
async def cb_topup_stars(callback: CallbackQuery, bot: Bot) -> None:
    """Выставить счёт в Stars на нужную сумму."""
    amount_rub = int(callback.data.split(":")[1])
    stars = max(1, round(amount_rub / RUB_PER_STAR))

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пополнение баланса",
        description=f"Зачисление {amount_rub} руб. на баланс магазина",
        payload=f"topup_stars:{callback.from_user.id}:{amount_rub}",
        currency="XTR",                          # ← Telegram Stars
        prices=[LabeledPrice(label="Stars", amount=stars)],  # ← amount = кол-во звёзд, без умножения
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    """Telegram требует ответить ok в течение 10 секунд."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message, session: AsyncSession
) -> None:
    """Платёж прошёл — зачисляем рубли на баланс."""
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload  # "topup_stars:{user_id}:{amount_rub}"

    try:
        _, uid_str, amount_str = payload.split(":")
        user_id = int(uid_str)
        amount_rub = float(amount_str)
    except Exception:
        return

    new_balance = await credit_balance(
        session=session,
        user_id=user_id,
        amount=amount_rub,
        description=f"Пополнение через Telegram Stars ({payment.total_amount} ⭐)",
    )

    await message.answer(
        f"✅ <b>Баланс пополнен!</b>\n\n"
        f"Оплачено: <b>{payment.total_amount} ⭐</b>\n"
        f"Зачислено: <b>+{amount_rub:.0f} руб.</b>\n"
        f"Текущий баланс: <b>{new_balance:.2f} руб.</b>",
        reply_markup=main_menu_kb(),
    )
