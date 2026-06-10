import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from keyboards.inline import (
    profile_kb, topup_kb, topup_method_kb, main_menu_kb, back_button
)
from lexicons.texts import (
    profile_text, topup_text, orders_history,
    BALANCE_UPDATED, INVALID_AMOUNT,
)
from services.payment_service import credit_balance
from utils.photo_utils import send_or_edit_photo, safe_edit

logger = logging.getLogger(__name__)
router = Router()


class TopupState(StatesGroup):
    waiting_custom_amount = State()


# ─── PROFILE ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await repo.get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    total_orders = await repo.get_total_orders_count(session, user.id)
    reg_date = user.created_at.strftime("%d.%m.%Y")
    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_profile,
        photo_unique_id=config.photo_unique_id_profile,
        text=profile_text(user.id, reg_date, user.balance, total_orders),
        reply_markup=profile_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:orders")
async def cb_orders_history(callback: CallbackQuery, session: AsyncSession) -> None:
    orders = await repo.get_user_orders(session, callback.from_user.id)
    await safe_edit(callback.message, 
        text=orders_history(orders),
        reply_markup=back_button("menu:profile"),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── TOPUP MENU ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:topup")
async def cb_topup_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopupState.waiting_custom_amount)
    await safe_edit(callback.message, 
        text=(
            "💳 <b>Пополнение баланса</b>\n\n"
            "Введите сумму в рублях или выберите готовый вариант.\n\n"
            "💳 Способы оплаты:\n"
            "• 🏦 <b>СБП</b> — оплата через Систему Быстрых Платежей\n"
            "• 💎 <b>TON</b> — оплата криптовалютой через @CryptoBot\n"
            "• ⭐️ <b>Telegram stars</b> — пополнение баланса через звезды"
        ),
        reply_markup=topup_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── PRESET AMOUNT ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("topup:"))
async def cb_topup_preset(callback: CallbackQuery, state: FSMContext) -> None:
    amount = int(callback.data.split(":")[1])
    await state.clear()
    await safe_edit(callback.message, 
        text=(
            f"💳 <b>Пополнение на {amount} руб.</b>\n\n"
            "Выберите способ оплаты:"
        ),
        reply_markup=topup_method_kb(amount),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── CUSTOM AMOUNT ───────────────────────────────────────────────────────────

@router.message(TopupState.waiting_custom_amount)
async def msg_topup_custom(message: Message, state: FSMContext) -> None:
    try:
        amount = int(message.text.strip())
        if amount < 10:
            raise ValueError
    except ValueError:
        await message.answer(INVALID_AMOUNT, parse_mode="HTML")
        return
    await state.clear()
    await message.answer(
        text=(
            f"💳 <b>Пополнение на {amount} руб.</b>\n\n"
            "Выберите способ оплаты:"
        ),
        reply_markup=topup_method_kb(amount),
        parse_mode="HTML",
    )



# ─── CRYPTOBOT (TON) ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("topup_ton:"))
async def cb_topup_ton(callback: CallbackQuery) -> None:
    amount = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    if not config.cryptobot_token:
        await callback.answer("❌ TON оплата временно недоступна", show_alert=True)
        return

    await callback.answer("⏳ Создаём инвойс...")

    try:
        from services.cryptobot_service import create_invoice
        invoice = await create_invoice(
            amount_rub=float(amount),
            user_id=user_id,
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"💎 Оплатить {invoice.amount} TON",
            url=invoice.url,
        ))
        builder.row(InlineKeyboardButton(
            text="🔙 Назад", callback_data="profile:topup"
        ))
        await safe_edit(callback.message, 
            text=(
                f"💎 <b>Оплата через TON</b>\n\n"
                f"Сумма в рублях: <b>{amount} руб.</b>\n"
                f"К оплате: <b>{invoice.amount} TON</b>\n"
                f"Срок действия: <b>30 минут</b>\n\n"
                "Нажмите кнопку — откроется @CryptoBot для оплаты.\n"
                "После оплаты баланс пополнится <b>автоматически</b>."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"CryptoBot invoice error: {e}")
        await safe_edit(callback.message, 
            text=f"❌ <b>Ошибка создания инвойса:</b> {e}\n\nПопробуйте позже.",
            reply_markup=back_button("profile:topup"),
            parse_mode="HTML",
        )


# ─── TELEGRAM PAYMENTS ───────────────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload
    try:
        _, uid_str, amount_str = payload.split(":")
        user_id = int(uid_str)
        amount = int(amount_str)
    except Exception:
        logger.error(f"Invalid payment payload: {payload}")
        return
    new_balance = await credit_balance(
        session=session,
        user_id=user_id,
        amount=float(amount),
        description=f"Пополнение через Telegram Payments {amount} руб.",
    )
    await message.answer(
        text=BALANCE_UPDATED(float(amount), new_balance),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
