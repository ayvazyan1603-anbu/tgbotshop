"""
Раздел подарков — полностью автоматический.

Флоу:
  1. Пользователь открывает раздел → бот вызывает getAvailableGifts и показывает список
  2. Пользователь вводит получателя (@username или user_id)
  3. Выбирает подарок из списка
  4. Подтверждает → бот списывает рубли с баланса и вызывает sendGift
  5. Telegram сам отправляет подарок, звёзды списываются с баланса бота
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from database.models import ItemType
from keyboards.inline import gift_list_kb, gift_confirm_kb, main_menu_kb, back_button
from lexicons.texts import gift_confirm, gift_enter_recipient, gift_list_text, NOT_ENOUGH_BALANCE
from services.payment_service import process_purchase, complete_purchase, refund_purchase
from utils.photo_utils import send_or_edit_photo, safe_edit

logger = logging.getLogger(__name__)
router = Router()


class GiftState(StatesGroup):
    waiting_recipient = State()


# ─── Открыть раздел ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:gift_regular")
async def cb_gifts_menu(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.clear()

    # Получаем актуальный список подарков прямо из Telegram API
    try:
        gifts_obj = await bot.get_available_gifts()
        tg_gifts = gifts_obj.gifts
    except Exception as e:
        logger.error(f"getAvailableGifts error: {e}")
        tg_gifts = []

    if not tg_gifts:
        await send_or_edit_photo(
            event=callback,
            photo_id=config.photo_id_gifts,
            photo_unique_id=config.photo_unique_id_gifts,
            text=(
                "🎁 <b>Магазин подарков</b>\n\n"
                "<i>Подарки временно недоступны. Попробуйте позже.</i>"
            ),
            reply_markup=back_button("menu:main"),
        )
        await callback.answer()
        return

    # Сохраняем список в FSM — чтобы не дёргать API повторно
    gifts_data = [
        {
            "id": g.id,
            "star_count": g.star_count,
            "total_count": g.total_count,       # None если не лимитированный
            "remaining_count": g.remaining_count,  # None если не лимитированный
            "sticker_emoji": g.sticker.emoji if g.sticker else "🎁",
        }
        for g in tg_gifts
    ]
    await state.update_data(tg_gifts=gifts_data)
    await state.set_state(GiftState.waiting_recipient)

    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_gifts,
        photo_unique_id=config.photo_unique_id_gifts,
        text=gift_enter_recipient(),
        reply_markup=back_button("menu:main"),
    )
    await callback.answer()


# ─── Получить получателя ─────────────────────────────────────────────────────

@router.message(GiftState.waiting_recipient)
async def msg_gift_recipient(message: Message, state: FSMContext) -> None:
    recipient = message.text.strip() if message.text else ""
    if not recipient:
        return

    data = await state.get_data()
    tg_gifts = data.get("tg_gifts", [])

    if not tg_gifts:
        await state.clear()
        await message.answer(
            "🎁 <b>Подарки временно недоступны.</b>",
            reply_markup=back_button("menu:main"),
            parse_mode="HTML",
        )
        return

    await state.update_data(recipient=recipient)
    await state.set_state(None)

    await message.answer(
        text=gift_list_text(recipient, tg_gifts),
        reply_markup=gift_list_kb(tg_gifts),
        parse_mode="HTML",
    )


# ─── Выбор подарка ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("gift_select:"))
async def cb_gift_select(callback: CallbackQuery, state: FSMContext) -> None:
    gift_tg_id = callback.data.split(":", 1)[1]  # строка — это gift_id из Telegram

    data = await state.get_data()
    tg_gifts = data.get("tg_gifts", [])
    recipient = data.get("recipient")

    gift = next((g for g in tg_gifts if g["id"] == gift_tg_id), None)
    if not gift:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    if not recipient:
        await callback.answer("Сначала укажите получателя", show_alert=True)
        return

    # Цена в Stars → в рублях (1 звезда ≈ 1.69 руб. по курсу Telegram)
    price_rub = _stars_to_rub(gift["star_count"])

    await state.update_data(selected_gift_id=gift_tg_id, selected_gift_price=price_rub)

    await safe_edit(
        callback.message,
        text=gift_confirm_text(gift, price_rub, recipient),
        reply_markup=gift_confirm_kb(gift_tg_id, recipient),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Подтверждение и отправка ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("gift_confirm:"))
async def cb_gift_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    parts = callback.data.split(":", 2)
    gift_tg_id = parts[1]
    recipient = parts[2]
    user_id = callback.from_user.id

    data = await state.get_data()
    price_rub = data.get("selected_gift_price")
    tg_gifts = data.get("tg_gifts", [])

    gift = next((g for g in tg_gifts if g["id"] == gift_tg_id), None)
    if not gift or price_rub is None:
        await callback.answer("❌ Сессия устарела, начните заново", show_alert=True)
        await state.clear()
        return

    # Списываем рубли с баланса
    order_id = await process_purchase(
        session=session,
        user_id=user_id,
        item_type=ItemType.GIFT_REGULAR,
        item_detail=f"Подарок {gift['sticker_emoji']} {gift['star_count']}⭐ → {recipient}",
        price=price_rub,
        description=f"Подарок {gift['star_count']} Stars",
    )

    if order_id is None:
        await safe_edit(
            callback.message,
            text=NOT_ENOUGH_BALANCE,
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Определяем user_id получателя
    recipient_user_id = await _resolve_recipient(bot, recipient)

    if recipient_user_id is None:
        # Не нашли пользователя — возврат средств
        await refund_purchase(session, order_id, user_id, price_rub)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Пользователь не найден</b>\n\n"
                f"Не удалось найти пользователя <code>{recipient}</code>.\n"
                "Убедитесь что username правильный и пользователь писал боту.\n\n"
                f"💳 <b>{price_rub:.0f} руб. возвращены на баланс.</b>"
            ),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Отправляем подарок через Telegram Bot API
    try:
        await bot.send_gift(
            user_id=recipient_user_id,
            gift_id=gift_tg_id,
            text=f"Подарок от нашего магазина! 🎁",
            text_parse_mode="HTML",
        )
    except TelegramBadRequest as e:
        logger.error(f"sendGift error: {e}")
        await refund_purchase(session, order_id, user_id, price_rub)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Ошибка отправки подарка</b>\n\n"
                f"<i>{e}</i>\n\n"
                f"💳 <b>{price_rub:.0f} руб. возвращены на баланс.</b>"
            ),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return
    except Exception as e:
        logger.error(f"sendGift unexpected error: {e}")
        await refund_purchase(session, order_id, user_id, price_rub)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Не удалось отправить подарок</b>\n\n"
                f"💳 <b>{price_rub:.0f} руб. возвращены на баланс.</b>"
            ),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Всё успешно
    await complete_purchase(session, order_id, f"Подарок {gift_tg_id} → {recipient}")
    await state.clear()

    await safe_edit(
        callback.message,
        text=(
            f"✅ <b>Подарок отправлен!</b>\n\n"
            f"{gift['sticker_emoji']} <b>{gift['star_count']} звёзд</b>\n"
            f"Получатель: <code>{recipient}</code>\n\n"
            "Подарок уже отображается в профиле получателя 🎉"
        ),
        reply_markup=gift_buy_more_kb(),
        parse_mode="HTML",
    )
    await callback.answer("✅ Подарок отправлен!")


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _stars_to_rub(star_count: int) -> float:
    """Конвертация Stars → рубли. 1 звезда ≈ 1.69 руб (курс Telegram)."""
    return round(star_count * 1.69, 2)


async def _resolve_recipient(bot: Bot, recipient: str) -> int | None:
    """
    Получить user_id по @username или числовому ID.
    Возвращает None если не удалось найти.
    """
    recipient = recipient.strip().lstrip("@")
    if recipient.isdigit():
        return int(recipient)
    # Пытаемся получить через getChat
    try:
        chat = await bot.get_chat(f"@{recipient}")
        return chat.id
    except Exception as e:
        logger.warning(f"_resolve_recipient failed for {recipient}: {e}")
        return None


def gift_confirm_text(gift: dict, price_rub: float, recipient: str) -> str:
    limited_info = ""
    if gift.get("total_count"):
        remaining = gift.get("remaining_count", 0)
        limited_info = f"\n🔥 Лимитированный: осталось <b>{remaining}</b> шт."

    return (
        f"🎁 <b>Подтверждение покупки</b>\n\n"
        f"Подарок: {gift['sticker_emoji']} <b>{gift['star_count']} ⭐</b>{limited_info}\n"
        f"Получатель: <code>{recipient}</code>\n"
        f"Стоимость: <b>{price_rub:.0f} руб.</b>\n\n"
        "После подтверждения подарок будет отправлен автоматически."
    )


def gift_buy_more_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Купить ещё подарок", callback_data="menu:gift_regular"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()
