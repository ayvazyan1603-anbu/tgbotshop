import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from database.models import ItemType
from keyboards.inline import gift_list_kb, gift_confirm_kb, main_menu_kb, back_button
from lexicons.texts import gifts_menu, gift_confirm, gift_enter_recipient, NOT_ENOUGH_BALANCE
from services.payment_service import process_purchase, complete_purchase

logger = logging.getLogger(__name__)
router = Router()


class GiftState(StatesGroup):
    waiting_recipient = State()


@router.callback_query(F.data.in_({"menu:gift_regular", "menu:gift_special"}))
async def cb_gifts_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    gift_type = "regular" if callback.data == "menu:gift_regular" else "special"
    gifts = await repo.get_gifts(session, gift_type)
    type_label = "обычных" if gift_type == "regular" else "особенных"

    if not gifts:
        await callback.message.edit_text(
            text=f"🎁 <b>Магазин {type_label} подарков</b>\n\n<i>Подарки временно недоступны.</i>",
            reply_markup=back_button("menu:main"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    emoji = "🎁" if gift_type == "regular" else "✨"
    title = "обычных" if gift_type == "regular" else "особенных (лимитированных)"
    await callback.message.edit_text(
        text=(
            f"{emoji} <b>Магазин {title} подарков</b>\n\n"
            + (
                "Выберите подарок для отправки другу или себе.\n"
                "Доставка занимает несколько минут." if gift_type == "regular"
                else "Особенные подарки — лимитированный тираж.\n"
                     "Могут расти в цене! Доставляются вручную администратором."
            )
        ),
        reply_markup=gift_list_kb(gifts, gift_type),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gift_select:"))
async def cb_gift_select(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    gift_id = int(callback.data.split(":")[1])
    gift = await repo.get_gift(session, gift_id)
    if not gift or not gift.is_available:
        await callback.answer("❌ Подарок недоступен", show_alert=True)
        return
    await state.update_data(gift_id=gift_id, gift_price=gift.price, gift_name=gift.name, gift_type=gift.gift_type)
    await state.set_state(GiftState.waiting_recipient)
    await callback.message.edit_text(
        text=gift_enter_recipient(),
        reply_markup=back_button("menu:main"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(GiftState.waiting_recipient)
async def msg_gift_recipient(message: Message, state: FSMContext) -> None:
    recipient = message.text.strip()
    data = await state.get_data()
    await state.clear()
    await message.answer(
        text=gift_confirm(data["gift_name"], data["gift_price"], recipient),
        reply_markup=gift_confirm_kb(data["gift_id"], recipient),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("gift_confirm:"))
async def cb_gift_confirm(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    parts = callback.data.split(":", 2)
    gift_id = int(parts[1])
    recipient = parts[2]
    user_id = callback.from_user.id

    gift = await repo.get_gift(session, gift_id)
    if not gift:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    item_type = ItemType.GIFT_SPECIAL if gift.gift_type == "special" else ItemType.GIFT_REGULAR
    order_id = await process_purchase(
        session=session, user_id=user_id,
        item_type=item_type, item_detail=f"{gift.name} → {recipient}",
        price=gift.price, description=f"Подарок: {gift.name}",
    )

    if order_id is None:
        await callback.message.edit_text(text=NOT_ENOUGH_BALANCE, reply_markup=main_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    # Уменьшить сток если лимитированный
    if gift.stock > 0:
        gift.stock -= 1
        if gift.stock == 0:
            gift.is_available = False
        await session.commit()

    # Уведомить админа
    try:
        await bot.send_message(
            chat_id=config.admin_id,
            text=(
                f"📦 <b>Новый заказ #{order_id}</b>\n\n"
                f"Товар: {gift.name}\n"
                f"Получатель: <code>{recipient}</code>\n"
                f"Сумма: <b>{gift.price:.2f} руб.</b>\n"
                f"Покупатель: <code>{user_id}</code>"
            ),
            reply_markup=__import__('keyboards.inline', fromlist=['admin_order_notify_kb']).admin_order_notify_kb(order_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

    await complete_purchase(session, order_id, f"{gift.name} → {recipient}")
    await callback.message.edit_text(
        text=(
            f"✅ <b>Заявка принята!</b>\n\n"
            f"Подарок: <b>{gift.name}</b>\n"
            f"Получатель: <code>{recipient}</code>\n\n"
            "Подарок будет отправлен в течение нескольких минут."
        ),
        reply_markup=main_menu_kb(), parse_mode="HTML",
    )
    await callback.answer("✅ Заказ оформлен!")
