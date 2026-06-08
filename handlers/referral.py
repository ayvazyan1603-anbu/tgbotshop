import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from keyboards.inline import referral_kb, main_menu_kb, back_button
from lexicons.texts import referral_text, WITHDRAWAL_REQUEST
from utils.photo_utils import send_or_edit_photo

logger = logging.getLogger(__name__)
router = Router()

MIN_WITHDRAWAL = 100.0


class WithdrawState(StatesGroup):
    waiting_amount = State()
    waiting_wallet = State()


@router.callback_query(F.data == "menu:referral")
async def cb_referral(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    user = await repo.get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    ref_count = await repo.get_referral_count(session, user.id)
    bot_info = await bot.get_me()

    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_referral,
        text=referral_text(
            bot_username=bot_info.username,
            user_id=user.id,
            ref_count=ref_count,
            ref_earned=user.ref_earned,
        ),
        reply_markup=referral_kb(),
    )
    await callback.answer()


# ─── WITHDRAWAL ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "referral:withdraw")
async def cb_referral_withdraw(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await repo.get_user(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    if user.balance < MIN_WITHDRAWAL:
        await callback.answer(
            f"❌ Минимальная сумма вывода: {MIN_WITHDRAWAL:.0f} руб.\n"
            f"Ваш баланс: {user.balance:.2f} руб.",
            show_alert=True,
        )
        return

    await state.set_state(WithdrawState.waiting_amount)
    await callback.message.edit_text(
        text=(
            f"💰 <b>Вывод средств</b>\n\n"
            f"Ваш текущий баланс: <b>{user.balance:.2f} руб.</b>\n"
            f"Минимальная сумма вывода: <b>{MIN_WITHDRAWAL:.0f} руб.</b>\n\n"
            "Введите сумму для вывода:"
        ),
        reply_markup=back_button("menu:referral"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(WithdrawState.waiting_amount)
async def msg_withdraw_amount(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount < MIN_WITHDRAWAL:
            raise ValueError
    except ValueError:
        await message.answer(
            f"❌ Введите корректную сумму (минимум {MIN_WITHDRAWAL:.0f} руб.)",
            parse_mode="HTML",
        )
        return

    user = await repo.get_user(session, message.from_user.id)
    if not user or user.balance < amount:
        await message.answer(
            "❌ Недостаточно средств на балансе.",
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.update_data(withdraw_amount=amount)
    await state.set_state(WithdrawState.waiting_wallet)
    await message.answer(
        text=(
            f"💳 <b>Введите реквизиты для вывода {amount:.2f} руб.</b>\n\n"
            "Номер карты, Тинькофф / QIWI / ЮMoney / крипто-адрес:"
        ),
        reply_markup=back_button("menu:referral"),
        parse_mode="HTML",
    )


@router.message(WithdrawState.waiting_wallet)
async def msg_withdraw_wallet(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    wallet = message.text.strip()
    data = await state.get_data()
    amount = data["withdraw_amount"]
    user_id = message.from_user.id
    await state.clear()

    user = await repo.get_user(session, user_id)
    if not user or user.balance < amount:
        await message.answer("❌ Недостаточно средств.", parse_mode="HTML")
        return

    # Debit balance
    await repo.update_balance(
        session, user_id, -amount, "withdraw",
        f"Вывод {amount:.2f} руб. на {wallet[:30]}"
    )

    # Notify admin
    try:
        await bot.send_message(
            chat_id=config.admin_id,
            text=(
                f"💸 <b>Заявка на вывод средств</b>\n\n"
                f"Пользователь: <code>{user_id}</code> "
                f"(@{message.from_user.username or 'нет'})\n"
                f"Сумма: <b>{amount:.2f} руб.</b>\n"
                f"Реквизиты: <code>{wallet}</code>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to notify admin about withdrawal: {e}")

    await message.answer(
        text=WITHDRAWAL_REQUEST(amount),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )