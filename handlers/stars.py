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
    stars_menu_kb, stars_confirm_kb, stars_recipient_kb,
    main_menu_kb, back_button, not_enough_balance_kb,
)
from lexicons.texts import (
    stars_menu, stars_enter_username, stars_custom_amount, stars_confirm,
    NOT_ENOUGH_BALANCE, STARS_ORDER_PLACED, INVALID_STARS_AMOUNT,
)
from services.payment_service import process_purchase, complete_purchase, refund_purchase
from services.fragment_service import (
    get_star_recipient, create_star_order, FragmentAPIError
)
from utils.photo_utils import send_or_edit_photo, safe_edit

logger = logging.getLogger(__name__)
router = Router()

STARS_PRICES: dict[int, int] = {
    50:    config.stars_50_price,
    100:   config.stars_100_price,
    150:   config.stars_150_price,
    250:   config.stars_250_price,
    350:   config.stars_350_price,
    500:   config.stars_500_price,
    750:   config.stars_750_price,
    1000:  config.stars_1000_price,
    1500:  config.stars_1500_price,
    2500:  config.stars_2500_price,
    5000:  config.stars_5000_price,
    10000: config.stars_10000_price,
}

PRICE_PER_STAR = config.stars_50_price / 50


def calc_stars_price(amount: int) -> float:
    if amount in STARS_PRICES:
        return float(STARS_PRICES[amount])
    return round(amount * PRICE_PER_STAR, 2)


class StarsState(StatesGroup):
    waiting_recipient = State()
    waiting_custom_amount = State()
    waiting_recipient_after_custom = State()


@router.callback_query(F.data == "menu:stars")
async def cb_stars_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_stars,
        photo_unique_id=config.photo_unique_id_stars,
        text=stars_menu(),
        reply_markup=stars_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stars:") & ~F.data.in_({"stars:custom"}))
async def cb_stars_select(callback: CallbackQuery, state: FSMContext) -> None:
    amount = int(callback.data.split(":")[1])
    price = calc_stars_price(amount)
    await state.update_data(stars_amount=amount, stars_price=price)
    await state.set_state(StarsState.waiting_recipient)
    await safe_edit(
        callback.message,
        text=(
            f"⭐ <b>{amount} Stars</b> — {price:.0f} руб.\n\n"
            "✏️ <b>Кому отправить Stars?</b>\n\n"
            "Нажмите <b>«Себе»</b> или введите <code>@username</code> / UID:"
        ),
        reply_markup=stars_recipient_kb(amount, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "stars:custom")
async def cb_stars_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(StarsState.waiting_custom_amount)
    await safe_edit(callback.message,
        text=stars_custom_amount(),
        reply_markup=back_button("menu:stars"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StarsState.waiting_custom_amount)
async def msg_stars_custom_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = int(message.text.strip())
        if amount < 50 or amount > 10000:
            raise ValueError
    except ValueError:
        await message.answer(INVALID_STARS_AMOUNT, parse_mode="HTML")
        return
    price = calc_stars_price(amount)
    await state.update_data(stars_amount=amount, stars_price=price)
    await state.set_state(StarsState.waiting_recipient_after_custom)
    await message.answer(
        text=(
            f"⭐ <b>{amount} Stars</b> — {price:.0f} руб.\n\n"
            "✏️ <b>Кому отправить Stars?</b>\n\n"
            "Нажмите <b>«Себе»</b> или введите <code>@username</code> / UID:"
        ),
        reply_markup=stars_recipient_kb(amount, message.from_user.id),
        parse_mode="HTML",
    )


# ─── Кнопка «Себе» для Stars ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("stars_self:"))
async def cb_stars_self(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    amount = int(parts[1])
    # Fragment API требует username, не user_id
    recipient = callback.from_user.username
    if not recipient:
        await callback.answer(
            "❌ У вас нет username в Telegram. Установите его в настройках профиля.",
            show_alert=True,
        )
        return
    recipient = recipient.lstrip("@")
    price = calc_stars_price(amount)
    await state.clear()
    await safe_edit(
        callback.message,
        text=stars_confirm(amount, price, "вам (себе)"),
        reply_markup=stars_confirm_kb(amount, recipient),
        parse_mode="HTML",
    )
    await callback.answer()


async def _handle_recipient(message: Message, state: FSMContext) -> None:
    recipient = message.text.strip()
    data = await state.get_data()
    amount = data["stars_amount"]
    price = data["stars_price"]
    await state.clear()
    await message.answer(
        text=stars_confirm(amount, price, recipient),
        reply_markup=stars_confirm_kb(amount, recipient),
        parse_mode="HTML",
    )


@router.message(StarsState.waiting_recipient)
async def msg_stars_recipient(message: Message, state: FSMContext) -> None:
    await _handle_recipient(message, state)


@router.message(StarsState.waiting_recipient_after_custom)
async def msg_stars_recipient_custom(message: Message, state: FSMContext) -> None:
    await _handle_recipient(message, state)


@router.callback_query(F.data.startswith("stars_confirm:"))
async def cb_stars_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext
) -> None:
    _, amount_str, recipient = callback.data.split(":", 2)
    amount = int(amount_str)
    price = calc_stars_price(amount)
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
        item_type=ItemType.STARS,
        item_detail=f"{amount} Stars → {recipient}",
        price=price,
        description=f"Покупка {amount} Stars",
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
            recipient_info = await get_star_recipient(recipient, amount)
            fragment_order = await create_star_order(
                username=recipient,
                recipient_hash=recipient_info.recipient_hash,
                quantity=amount,
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
                    f"⭐ <b>{amount} Stars</b> → <code>{recipient}</code>\n\n"
                    "Доставка обычно занимает 1–3 минуты.\n"
                    "Вы получите уведомление, когда Stars будут зачислены."
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
                    f"💳 <b>{price:.2f} руб. возвращены на ваш баланс.</b>\n\n"
                    "Попробуйте ещё раз или обратитесь в поддержку."
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
                        f"Товар: ⭐ {amount} Stars → <code>{recipient}</code>\n"
                        f"Покупатель: <code>{user_id}</code>\n"
                        f"Ошибка: {e}"
                    ),
                    reply_markup=admin_order_notify_kb(order_id),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            await safe_edit(callback.message,
                text=STARS_ORDER_PLACED(amount, recipient),
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
                    f"Товар: ⭐ {amount} Telegram Stars\n"
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
            text=STARS_ORDER_PLACED(amount, recipient),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
