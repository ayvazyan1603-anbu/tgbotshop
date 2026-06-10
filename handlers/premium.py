import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from database.models import ItemType
from keyboards.inline import (
    premium_menu_kb, premium_confirm_kb, premium_recipient_kb,
    main_menu_kb, back_button, not_enough_balance_kb,
)
from lexicons.texts import (
    premium_menu, premium_enter_username, premium_confirm,
    NOT_ENOUGH_BALANCE, PREMIUM_ORDER_PLACED,
)
from services.payment_service import process_purchase, complete_purchase, refund_purchase
from services.fragment_service import (
    get_premium_recipient, create_premium_order, FragmentAPIError
)
from utils.photo_utils import send_or_edit_photo, safe_edit

logger = logging.getLogger(__name__)
router = Router()

PREMIUM_PRICES: dict[int, int] = {
    3:  config.premium_3m_price,
    6:  config.premium_6m_price,
    12: config.premium_12m_price,
}


class PremiumState(StatesGroup):
    waiting_recipient = State()


@router.callback_query(F.data == "menu:premium")
async def cb_premium_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_premium,
        photo_unique_id=config.photo_unique_id_premium,
        text=premium_menu(),
        reply_markup=premium_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("premium:"))
async def cb_premium_select(callback: CallbackQuery, state: FSMContext) -> None:
    months = int(callback.data.split(":")[1])
    price = float(PREMIUM_PRICES[months])
    await state.update_data(premium_months=months, premium_price=price)
    await state.set_state(PremiumState.waiting_recipient)
    await safe_edit(
        callback.message,
        text=(
            f"💎 <b>Telegram Premium {months} мес.</b> — {price:.0f} руб.\n\n"
            "✏️ <b>Кому подарить Premium?</b>\n\n"
            "Нажмите <b>«Себе»</b> или введите <code>@username</code> / UID:"
        ),
        reply_markup=premium_recipient_kb(months, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Кнопка «Себе» для Premium ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("premium_self:"))
async def cb_premium_self(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    months = int(parts[1])
    recipient = callback.from_user.username
    if not recipient:
        await callback.answer(
            "❌ У вас нет username в Telegram. Установите его в настройках профиля.",
            show_alert=True,
        )
        return
    recipient = recipient.lstrip("@")
    price = float(PREMIUM_PRICES[months])
    await state.clear()
    await safe_edit(
        callback.message,
        text=premium_confirm(months, price, "вам (себе)"),
        reply_markup=premium_confirm_kb(months, recipient),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PremiumState.waiting_recipient)
async def msg_premium_recipient(message: Message, state: FSMContext) -> None:
    recipient = message.text.strip()
    data = await state.get_data()
    months = data["premium_months"]
    price = data["premium_price"]
    await state.clear()
    await message.answer(
        text=premium_confirm(months, price, recipient),
        reply_markup=premium_confirm_kb(months, recipient),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("premium_confirm:"))
async def cb_premium_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext
) -> None:
    _, months_str, recipient = callback.data.split(":", 2)
    months = int(months_str)
    price = float(PREMIUM_PRICES[months])
    user_id = callback.from_user.id

    # Проверяем баланс заранее
    user = await repo.get_user(session, user_id)
    if not user or user.balance < price:
        needed = max(int(price - (user.balance if user else 0)), 10)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Недостаточно средств!</b>\n\n"
                f"Нужно: <b>{price:.0f} руб.</b>\n"
                f"На балансе: <b>{user.balance:.0f} руб.</b>\n\n"
                f"Пополните баланс на <b>{needed} руб.</b> и попробуйте снова."
            ),
            reply_markup=not_enough_balance_kb(needed),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    from handlers.admin import INFINITE_BALANCE_KEY
    infinite = (await state.get_data()).get(INFINITE_BALANCE_KEY, False)

    order_id = await process_purchase(
        session=session,
        user_id=user_id,
        item_type=ItemType.PREMIUM,
        item_detail=f"Premium {months}m → {recipient}",
        price=price,
        description=f"Telegram Premium {months} мес.",
        infinite_balance=infinite,
    )
    if order_id is None:
        needed = max(int(price), 10)
        await safe_edit(
            callback.message,
            text="❌ <b>Недостаточно средств!</b>",
            reply_markup=not_enough_balance_kb(needed),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer("⏳ Отправляем заказ на Fragment...")

    if config.fragment_api_key:
        try:
            recipient_info = await get_premium_recipient(recipient, months)
            fragment_order = await create_premium_order(
                username=recipient,
                recipient_hash=recipient_info.recipient_hash,
                months=months,
            )
            from database.models import Order
            from sqlalchemy import select
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one()
            order.delivery_data = fragment_order.order_id
            await session.commit()

            await safe_edit(callback.message,
                text=(
                    f"✅ <b>Заказ #{order_id} отправлен!</b>\n\n"
                    f"💎 <b>Premium {months} мес.</b> → <code>{recipient}</code>\n\n"
                    "Доставка обычно занимает 1–3 минуты.\n"
                    "Вы получите уведомление, когда подписка будет активирована."
                ),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )

        except FragmentAPIError as e:
            logger.error(f"Fragment API error for order {order_id}: {e}")
            await refund_purchase(session, order_id, user_id, price)
            await safe_edit(callback.message,
                text=(
                    f"❌ <b>Ошибка при отправке заказа:</b> {e}\n\n"
                    f"💳 <b>{price:.2f} руб. возвращены на ваш баланс.</b>"
                ),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Unexpected error for order {order_id}: {e}")
            try:
                from keyboards.inline import admin_order_notify_kb
                await bot.send_message(
                    chat_id=config.admin_id,
                    text=(
                        f"⚠️ <b>Ошибка Fragment API — заказ #{order_id}</b>\n\n"
                        f"Товар: 💎 Premium {months}м → <code>{recipient}</code>\n"
                        f"Покупатель: <code>{user_id}</code>\n"
                        f"Ошибка: {e}"
                    ),
                    reply_markup=admin_order_notify_kb(order_id),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            await safe_edit(callback.message,
                text=PREMIUM_ORDER_PLACED(months, recipient),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
    else:
        try:
            from keyboards.inline import admin_order_notify_kb
            await bot.send_message(
                chat_id=config.admin_id,
                text=(
                    f"📦 <b>Новый заказ #{order_id}</b>\n\n"
                    f"Товар: 💎 Telegram Premium {months} мес.\n"
                    f"Получатель: <code>{recipient}</code>\n"
                    f"Сумма: <b>{price:.2f} руб.</b>\n"
                    f"Покупатель ID: <code>{user_id}</code>"
                ),
                reply_markup=admin_order_notify_kb(order_id),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        await complete_purchase(session, order_id, f"Recipient: {recipient}")
        await safe_edit(callback.message,
            text=PREMIUM_ORDER_PLACED(months, recipient),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
