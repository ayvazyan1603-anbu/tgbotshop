"""
Раздел подарков — полностью автоматический через Bot API sendGift.

Флоу:
  1. Пользователь открывает раздел → бот показывает список уникальных подарков
  2. Пользователь нажимает кнопку подарка
  3. Выбирает "Себе" или вводит @username получателя
  4. Подтверждает → бот списывает рубли с баланса и вызывает sendGift
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from database.models import ItemType
from keyboards.inline import main_menu_kb, back_button
from services.payment_service import process_purchase, complete_purchase, refund_purchase
from utils.photo_utils import send_or_edit_photo, safe_edit

logger = logging.getLogger(__name__)
router = Router()

# ─── Каталог подарков (gift_id из Telegram) ──────────────────────────────────
# Сопоставлено по скриншоту: [1]Новогодний мишка [2]Мишка влюблённых [3]Ёлка
# [4]Сердце влюблённых [5]Мишка на 8 марта [6]Мишка на День Патрика
# [7]Мишка на 1 апреля [8]Мишка на Пасху [9]Мишка на 1 мая

UNIQUE_GIFTS = [
    {"id": "5956217000635139069",  "emoji": "🐻",  "name": "Новогодний мишка",       "price_rub": 100},
    {"id": "5922558454332916696",  "emoji": "🐻",  "name": "Мишка влюблённых",       "price_rub": 100},
    {"id": "5800655655995968830",  "emoji": "🎄",  "name": "Ёлка",                   "price_rub": 100},
    {"id": "5801108895304779062",  "emoji": "💝",  "name": "Сердце влюблённых",      "price_rub": 100},
    {"id": "5866352046986232958",  "emoji": "🐻",  "name": "Мишка на 8 марта",       "price_rub": 100},
    {"id": "5893356958802511476",  "emoji": "🐻",  "name": "Мишка на День Патрика",  "price_rub": 100},
    {"id": "5935895822435615975",  "emoji": "🐻",  "name": "Мишка на 1 апреля",      "price_rub": 100},
    {"id": "5969796561943660080",  "emoji": "🐻",  "name": "Мишка на Пасху",         "price_rub": 100},
    {"id": "6026193266406327981",  "emoji": "🐻",  "name": "Мишка на 1 мая",         "price_rub": 100},
]


class GiftState(StatesGroup):
    waiting_recipient = State()


def _get_gift_by_id(gift_id: str) -> dict | None:
    return next((g for g in UNIQUE_GIFTS if g["id"] == gift_id), None)


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def gifts_list_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(0, len(UNIQUE_GIFTS), 2):
        row_gifts = UNIQUE_GIFTS[i:i + 2]
        row = [
            InlineKeyboardButton(
                text=f"{g['emoji']} [{i + j + 1}] | {g['price_rub']} руб.",
                callback_data=f"gift_select:{g['id']}",
            )
            for j, g in enumerate(row_gifts)
        ]
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def gift_recipient_kb(gift_id: str, self_user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🙋 Себе",
        callback_data=f"gift_self:{gift_id}:{self_user_id}",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:gift_regular"))
    return builder.as_markup()


def gift_confirm_kb(gift_id: str, recipient: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"gift_confirm:{gift_id}:{recipient}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu:gift_regular"),
    )
    return builder.as_markup()


def gift_buy_more_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Купить ещё подарок", callback_data="menu:gift_regular"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def not_enough_balance_kb(needed: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"💳 Пополнить на {needed} руб.",
        callback_data=f"topup:{needed}",
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


# ─── Открыть раздел ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:gift_regular")
async def cb_gifts_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()

    names_list = "\n".join(
        f"[{i + 1}] — {g['emoji']} {g['name']}"
        for i, g in enumerate(UNIQUE_GIFTS)
    )

    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_gifts,
        photo_unique_id=config.photo_unique_id_gifts,
        text=(
            "🎁 <b>Удалённые подарки</b>\n\n"
            f"{names_list}\n\n"
            "Выберите подарок:"
        ),
        reply_markup=gifts_list_kb(),
    )
    await callback.answer()


# ─── Выбор подарка ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("gift_select:"))
async def cb_gift_select(callback: CallbackQuery, state: FSMContext) -> None:
    gift_id = callback.data.split(":", 1)[1]
    gift = _get_gift_by_id(gift_id)
    if not gift:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    await state.update_data(selected_gift_id=gift_id)
    await state.set_state(GiftState.waiting_recipient)

    await safe_edit(
        callback.message,
        text=(
            f"{gift['emoji']} <b>{gift['name']}</b>\n"
            f"Стоимость: <b>{gift['price_rub']} руб.</b>\n\n"
            "✏️ <b>Кому отправить подарок?</b>\n\n"
            "Нажмите <b>«Себе»</b> или введите <code>@username</code> / UID получателя:"
        ),
        reply_markup=gift_recipient_kb(gift_id, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Кнопка "Себе" ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("gift_self:"))
async def cb_gift_self(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    gift_id = parts[1]
    recipient = str(callback.from_user.id)

    gift = _get_gift_by_id(gift_id)
    if not gift:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    await state.update_data(selected_gift_id=gift_id)
    await state.set_state(None)

    await safe_edit(
        callback.message,
        text=_confirm_text(gift, recipient, is_self=True),
        reply_markup=gift_confirm_kb(gift_id, recipient),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Ввод получателя вручную ─────────────────────────────────────────────────

@router.message(GiftState.waiting_recipient)
async def msg_gift_recipient(message: Message, state: FSMContext) -> None:
    recipient = message.text.strip() if message.text else ""
    if not recipient:
        return

    data = await state.get_data()
    gift_id = data.get("selected_gift_id")
    gift = _get_gift_by_id(gift_id) if gift_id else None

    if not gift:
        await state.clear()
        await message.answer("❌ Сессия устарела, начните заново.", reply_markup=main_menu_kb(), parse_mode="HTML")
        return

    await state.set_state(None)

    await message.answer(
        text=_confirm_text(gift, recipient, is_self=False),
        reply_markup=gift_confirm_kb(gift_id, recipient),
        parse_mode="HTML",
    )


# ─── Подтверждение и отправка ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("gift_confirm:"))
async def cb_gift_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    parts = callback.data.split(":", 2)
    gift_id = parts[1]
    recipient = parts[2]
    user_id = callback.from_user.id

    gift = _get_gift_by_id(gift_id)
    if not gift:
        await callback.answer("❌ Сессия устарела, начните заново", show_alert=True)
        await state.clear()
        return

    price_rub = float(gift["price_rub"])

    # Проверяем баланс заранее чтобы сразу предложить пополнение
    user = await repo.get_user(session, user_id)
    if not user or user.balance < price_rub:
        needed = int(price_rub - (user.balance if user else 0))
        needed = max(needed, 10)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Недостаточно средств!</b>\n\n"
                f"Нужно: <b>{price_rub:.0f} руб.</b>\n"
                f"На балансе: <b>{user.balance:.0f if user else 0} руб.</b>\n\n"
                f"Пополните баланс на <b>{needed} руб.</b> и попробуйте снова."
            ),
            reply_markup=not_enough_balance_kb(needed),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Списываем баланс
    order_id = await process_purchase(
        session=session,
        user_id=user_id,
        item_type=ItemType.GIFT_REGULAR,
        item_detail=f"{gift['emoji']} {gift['name']} → {recipient}",
        price=price_rub,
        description=f"Подарок {gift['name']}",
    )

    if order_id is None:
        needed = int(price_rub)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Недостаточно средств!</b>\n\n"
                f"Пополните баланс и попробуйте снова."
            ),
            reply_markup=not_enough_balance_kb(needed),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Определяем user_id получателя
    recipient_user_id = await _resolve_recipient(bot, recipient)

    if recipient_user_id is None:
        await refund_purchase(session, order_id, user_id, price_rub)
        await safe_edit(
            callback.message,
            text=(
                "❌ <b>Пользователь не найден</b>\n\n"
                f"Не удалось найти <code>{recipient}</code>.\n"
                "Убедитесь что username правильный и пользователь писал боту.\n\n"
                f"💳 <b>{price_rub:.0f} руб. возвращены на баланс.</b>"
            ),
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Отправляем подарок
    try:
        await bot.send_gift(
            user_id=recipient_user_id,
            gift_id=gift_id,
            text=f"Подарок от нашего магазина! {gift['emoji']}",
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
        logger.error(f"sendGift unexpected: {e}")
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

    await complete_purchase(session, order_id, f"{gift_id} → {recipient}")
    await state.clear()

    await safe_edit(
        callback.message,
        text=(
            f"✅ <b>Подарок отправлен!</b>\n\n"
            f"{gift['emoji']} <b>{gift['name']}</b>\n"
            f"Получатель: <code>{recipient}</code>\n\n"
            "Подарок уже отображается в профиле получателя 🎉"
        ),
        reply_markup=gift_buy_more_kb(),
        parse_mode="HTML",
    )
    await callback.answer("✅ Подарок отправлен!")


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _confirm_text(gift: dict, recipient: str, is_self: bool) -> str:
    recipient_label = "вам" if is_self else f"<code>{recipient}</code>"
    return (
        f"🎁 <b>Подтверждение покупки</b>\n\n"
        f"Подарок: {gift['emoji']} <b>{gift['name']}</b>\n"
        f"Получатель: {recipient_label}\n"
        f"Стоимость: <b>{gift['price_rub']} руб.</b>\n\n"
        "После подтверждения подарок будет отправлен автоматически."
    )


async def _resolve_recipient(bot: Bot, recipient: str) -> int | None:
    recipient = recipient.strip().lstrip("@")
    if recipient.isdigit():
        return int(recipient)
    try:
        chat = await bot.get_chat(f"@{recipient}")
        return chat.id
    except Exception as e:
        logger.warning(f"_resolve_recipient failed for {recipient}: {e}")
        return None
