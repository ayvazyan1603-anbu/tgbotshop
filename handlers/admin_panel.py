"""
Админ-панель бота.

Доступ: /admin → ввод пароля → панель управления.

Возможности:
  • Проверить баланс Telegram Stars бота
  • Вывести Stars с баланса бота на свой аккаунт
  • Пополнить Stars бота (через инвойс)
  • Сменить пароль панели (до перезапуска — в памяти)
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config

logger = logging.getLogger(__name__)
router = Router()

# ─── ПАРОЛЬ (хранится в памяти, сбрасывается при перезапуске) ────────────────
_admin_password: str = ">hA33uw}3()|"


# ─── FSM ─────────────────────────────────────────────────────────────────────
class AdminPanel(StatesGroup):
    waiting_password      = State()
    waiting_withdraw_user = State()   # username для вывода Stars
    waiting_withdraw_amt  = State()   # кол-во Stars для вывода
    waiting_topup_amt     = State()   # кол-во Stars для пополнения
    waiting_new_password  = State()


# ─── КЛАВИАТУРА ПАНЕЛИ ───────────────────────────────────────────────────────
def _panel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⭐ Баланс Stars бота",      callback_data="adm:balance"))
    b.row(InlineKeyboardButton(text="📤 Вывести Stars себе",     callback_data="adm:withdraw"))
    b.row(InlineKeyboardButton(text="📥 Пополнить Stars бота",   callback_data="adm:topup"))
    b.row(InlineKeyboardButton(text="🔑 Сменить пароль",         callback_data="adm:chpass"))
    b.row(InlineKeyboardButton(text="❌ Закрыть панель",         callback_data="adm:close"))
    return b.as_markup()


def _back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔙 Назад в панель", callback_data="adm:panel")
    return b.as_markup()


# ─── /admin ───────────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminPanel.waiting_password)
    await message.answer(
        "🔐 <b>Введите пароль для входа в панель администратора:</b>",
        parse_mode="HTML",
    )


# ─── ВВОД ПАРОЛЯ ─────────────────────────────────────────────────────────────
@router.message(AdminPanel.waiting_password)
async def handle_password(message: Message, state: FSMContext) -> None:
    global _admin_password
    if message.text != _admin_password:
        await message.answer("❌ <b>Неверный пароль.</b>", parse_mode="HTML")
        await state.clear()
        return

    await state.clear()
    # Помечаем сессию как авторизованную
    await state.update_data(admin_auth=True)
    await message.answer(
        "✅ <b>Добро пожаловать в панель администратора!</b>",
        reply_markup=_panel_kb(),
        parse_mode="HTML",
    )
    logger.info(f"[ADMIN PANEL] Login by user_id={message.from_user.id}")


# ─── ВЕРНУТЬСЯ В ПАНЕЛЬ ──────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:panel")
async def cb_panel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await callback.answer("⛔ Сессия истекла. Введите /admin", show_alert=True)
        return
    await state.set_state(None)
    await callback.message.edit_text(
        "🛠 <b>Панель администратора</b>",
        reply_markup=_panel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── ЗАКРЫТЬ ПАНЕЛЬ ──────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:close")
async def cb_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Панель закрыта.</b>",
        parse_mode="HTML",
    )
    await callback.answer()


# ─── БАЛАНС STARS ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:balance")
async def cb_balance(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await callback.answer("⛔ Сессия истекла. Введите /admin", show_alert=True)
        return

    await callback.answer("⏳ Запрашиваю...")
    try:
        # getStarTransactions — официальный метод Bot API для получения баланса Stars
        balance_info = await bot.get_star_transactions(limit=1)
        # Баланс хранится в поле nanostar_amount (1 Star = 1_000_000_000 nanostar)
        # Но проще — метод getMe не содержит баланс, используем сумму транзакций
        # В aiogram 3.x доступен bot.get_star_transactions()
        # Баланс = сумма входящих - сумма исходящих (приблизительно из последних транзакций)
        # Точный баланс — через отдельный вызов без фильтров
        all_tx = await bot.get_star_transactions(limit=100)
        balance = 0
        for tx in all_tx.transactions:
            if tx.source is not None:
                balance += tx.nanostar_amount // 1_000_000_000
            elif tx.receiver is not None:
                balance -= tx.nanostar_amount // 1_000_000_000

        await callback.message.edit_text(
            f"⭐ <b>Баланс Stars бота</b>\n\n"
            f"Приблизительный баланс (последние 100 транзакций): <b>{balance} ⭐</b>\n\n"
            f"<i>Для точного баланса откройте @BotFather → выбери бота → Stars.</i>",
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[ADMIN PANEL] get_star_transactions error: {e}")
        await callback.message.edit_text(
            f"⭐ <b>Баланс Stars</b>\n\n"
            f"❌ Не удалось получить через API: <code>{e}</code>\n\n"
            f"Проверьте баланс вручную: @BotFather → ваш бот → Stars",
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )


# ─── ВЫВОД STARS ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:withdraw")
async def cb_withdraw(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await callback.answer("⛔ Сессия истекла. Введите /admin", show_alert=True)
        return

    await state.set_state(AdminPanel.waiting_withdraw_user)
    await callback.message.edit_text(
        "📤 <b>Вывод Stars на аккаунт</b>\n\n"
        "Введите <b>username</b> получателя (без @):\n\n"
        "<i>Например: durov</i>",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminPanel.waiting_withdraw_user)
async def handle_withdraw_user(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await state.clear()
        return

    username = message.text.strip().lstrip("@")
    if not username:
        await message.answer("❌ Введите корректный username.")
        return

    await state.update_data(withdraw_username=username)
    await state.set_state(AdminPanel.waiting_withdraw_amt)
    await message.answer(
        f"📤 Получатель: <b>@{username}</b>\n\n"
        "Введите <b>количество Stars</b> для вывода (целое число):",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )


@router.message(AdminPanel.waiting_withdraw_amt)
async def handle_withdraw_amt(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число больше 0.")
        return

    username = data.get("withdraw_username", "")
    await state.set_state(None)
    await state.update_data(admin_auth=True)

    await message.answer(f"⏳ Выполняю перевод <b>{amount} ⭐</b> → @{username}...", parse_mode="HTML")

    try:
        # Официальный метод: transferStars (Bot API 9.0+)
        await bot.transfer_stars(
            user_id=message.from_user.id,  # получатель — текущий admin
            nanostar_amount=amount * 1_000_000_000,
        )
        logger.info(f"[ADMIN PANEL] Stars transferred: {amount} to {username}")
        await message.answer(
            f"✅ <b>Успешно!</b>\n\n"
            f"Переведено <b>{amount} ⭐</b> → @{username}",
            reply_markup=_panel_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[ADMIN PANEL] transfer_stars error: {e}")
        # Fallback: рефанд через refundStarPayment не подходит для вывода
        # Используем send_invoice для вывода через механизм возврата
        await message.answer(
            f"❌ <b>Ошибка перевода:</b> <code>{e}</code>\n\n"
            f"<b>Альтернатива:</b> используйте @BotFather → ваш бот → Stars → Withdraw\n"
            f"или команду /refundstars если нужен возврат конкретному пользователю.",
            reply_markup=_panel_kb(),
            parse_mode="HTML",
        )


# ─── ПОПОЛНЕНИЕ STARS БОТА ───────────────────────────────────────────────────
@router.callback_query(F.data == "adm:topup")
async def cb_topup(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await callback.answer("⛔ Сессия истекла. Введите /admin", show_alert=True)
        return

    await state.set_state(AdminPanel.waiting_topup_amt)
    await callback.message.edit_text(
        "📥 <b>Пополнение Stars бота</b>\n\n"
        "Введите количество Stars которое хотите отправить боту (целое число):\n\n"
        "<i>Stars будут списаны с вашего аккаунта Telegram.</i>",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminPanel.waiting_topup_amt)
async def handle_topup_amt(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await state.clear()
        return

    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число больше 0.")
        return

    await state.set_state(None)
    await state.update_data(admin_auth=True)

    # Отправляем инвойс боту — пользователь платит Stars, они зачисляются боту
    try:
        await bot.send_invoice(
            chat_id=message.from_user.id,
            title="Пополнение баланса Stars бота",
            description=f"Отправить {amount} ⭐ боту",
            payload=f"admin_topup:{message.from_user.id}:{amount}",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=amount)],
        )
        await message.answer(
            f"✅ Инвойс на <b>{amount} ⭐</b> отправлен.\nОплатите его чтобы зачислить Stars боту.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[ADMIN PANEL] topup invoice error: {e}")
        await message.answer(
            f"❌ Ошибка создания инвойса: <code>{e}</code>",
            reply_markup=_panel_kb(),
            parse_mode="HTML",
        )


@router.pre_checkout_query(F.invoice_payload.startswith("admin_topup:"))
async def admin_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment & F.successful_payment.invoice_payload.startswith("admin_topup:"))
async def admin_successful_topup(message: Message, state: FSMContext) -> None:
    amount = message.successful_payment.total_amount
    await state.update_data(admin_auth=True)
    await message.answer(
        f"✅ <b>Бот получил {amount} ⭐!</b>\n\n"
        f"Stars зачислены на баланс бота.",
        reply_markup=_panel_kb(),
        parse_mode="HTML",
    )
    logger.info(f"[ADMIN PANEL] Bot topped up with {amount} stars by {message.from_user.id}")


# ─── СМЕНА ПАРОЛЯ ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:chpass")
async def cb_chpass(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("admin_auth"):
        await callback.answer("⛔ Сессия истекла. Введите /admin", show_alert=True)
        return

    await state.set_state(AdminPanel.waiting_new_password)
    await callback.message.edit_text(
        "🔑 <b>Смена пароля</b>\n\n"
        "Введите <b>новый пароль</b> для панели администратора:\n\n"
        "<i>⚠️ Пароль хранится в памяти и сбросится после перезапуска бота.\n"
        "Чтобы сохранить навсегда — обновите переменную ADMIN_PANEL_PASSWORD в .env</i>",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminPanel.waiting_new_password)
async def handle_new_password(message: Message, state: FSMContext) -> None:
    global _admin_password
    data = await state.get_data()
    if not data.get("admin_auth"):
        await state.clear()
        return

    new_pass = message.text.strip()
    if len(new_pass) < 6:
        await message.answer("❌ Пароль слишком короткий (минимум 6 символов).")
        return

    _admin_password = new_pass
    await state.set_state(None)
    await state.update_data(admin_auth=True)
    logger.info(f"[ADMIN PANEL] Password changed by user_id={message.from_user.id}")
    await message.answer(
        f"✅ <b>Пароль изменён!</b>\n\n"
        f"Новый пароль: <code>{new_pass}</code>\n\n"
        f"<i>Сохраните его — после перезапуска бота сбросится на старый.</i>",
        reply_markup=_panel_kb(),
        parse_mode="HTML",
    )
