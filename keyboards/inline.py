from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config


# ─── MAIN MENU ───────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌟 Купить Stars", callback_data="menu:stars"),
        InlineKeyboardButton(text="💎 Купить Premium", callback_data="menu:premium"),
    )
    builder.row(InlineKeyboardButton(text="🎁 Удалённые подарки", callback_data="menu:gift_regular"))
    builder.row(InlineKeyboardButton(text="🌐 Купить VPN", callback_data="menu:vpn"))
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
        InlineKeyboardButton(text="🤝 Партнёрская сеть", callback_data="menu:referral"),
    )
    builder.row(InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu:support"))
    return builder.as_markup()


# ─── NAV ─────────────────────────────────────────────────────────────────────

def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Главное меню", callback_data="menu:main")
    return builder.as_markup()


def back_button(callback: str, label: str = "🔙 Назад") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=label, callback_data=callback)
    return builder.as_markup()


def not_enough_balance_kb(needed: int) -> InlineKeyboardMarkup:
    """Кнопка редиректа на пополнение нужной суммы."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"💳 Пополнить на {needed} руб.",
        callback_data=f"topup:{needed}",
    ))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


# ─── STARS ───────────────────────────────────────────────────────────────────

def stars_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    tiers = [
        (50,    config.stars_50_price),
        (100,   config.stars_100_price),
        (150,   config.stars_150_price),
        (250,   config.stars_250_price),
        (350,   config.stars_350_price),
        (500,   config.stars_500_price),
        (750,   config.stars_750_price),
        (1000,  config.stars_1000_price),
        (1500,  config.stars_1500_price),
        (2500,  config.stars_2500_price),
        (5000,  config.stars_5000_price),
        (10000, config.stars_10000_price),
    ]
    for i in range(0, len(tiers), 2):
        row = [
            InlineKeyboardButton(
                text=f"⭐ {amount} — {price} руб.",
                callback_data=f"stars:{amount}",
            )
            for amount, price in tiers[i:i+2]
        ]
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="⭐ Свой вариант", callback_data="stars:custom"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


def stars_recipient_kb(amount: int, self_user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора получателя Stars — с кнопкой «Себе»."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🙋 Себе",
        callback_data=f"stars_self:{amount}:{self_user_id}",
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:stars"))
    return builder.as_markup()


def stars_confirm_kb(amount: int, recipient: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"stars_confirm:{amount}:{recipient}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu:stars"),
    )
    return builder.as_markup()


# ─── PREMIUM ─────────────────────────────────────────────────────────────────

def premium_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"📅 3 месяца — {config.premium_3m_price} руб.", callback_data="premium:3"))
    builder.row(InlineKeyboardButton(text=f"📅 6 месяцев — {config.premium_6m_price} руб.", callback_data="premium:6"))
    builder.row(InlineKeyboardButton(text=f"📅 12 месяцев — {config.premium_12m_price} руб.", callback_data="premium:12"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


def premium_recipient_kb(months: int, self_user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора получателя Premium — с кнопкой «Себе»."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🙋 Себе",
        callback_data=f"premium_self:{months}:{self_user_id}",
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:premium"))
    return builder.as_markup()


def premium_confirm_kb(months: int, recipient: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"premium_confirm:{months}:{recipient}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu:premium"),
    )
    return builder.as_markup()


# ─── GIFTS ───────────────────────────────────────────────────────────────────

def gift_list_kb(tg_gifts: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = []
    for g in tg_gifts:
        limited = f" [{g['remaining_count']}шт]" if g.get("total_count") else ""
        buttons.append(InlineKeyboardButton(
            text=f"{g['sticker_emoji']} {g['star_count']}⭐{limited}",
            callback_data=f"gift_select:{g['id']}",
        ))
    for i in range(0, len(buttons), 2):
        builder.row(*buttons[i:i + 2])
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def gift_confirm_kb(gift_tg_id: str, recipient: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"gift_confirm:{gift_tg_id}:{recipient}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"),
    )
    return builder.as_markup()


# ─── VPN ─────────────────────────────────────────────────────────────────────

def vpn_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"🚀 1 месяц — {config.vpn_1m_price} руб.", callback_data="vpn:30"))
    builder.row(InlineKeyboardButton(text=f"🚀 3 месяца — {config.vpn_3m_price} руб.", callback_data="vpn:90"))
    builder.row(InlineKeyboardButton(text=f"🚀 6 месяцев — {config.vpn_6m_price} руб.", callback_data="vpn:180"))
    builder.row(InlineKeyboardButton(text="❓ Инструкция по настройке", callback_data="vpn:instruction"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


# ─── PROFILE ─────────────────────────────────────────────────────────────────

def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="profile:topup"))
    builder.row(InlineKeyboardButton(text="📜 История покупок", callback_data="profile:orders"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def topup_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💵 100 руб.", callback_data="topup:100"),
        InlineKeyboardButton(text="💵 500 руб.", callback_data="topup:500"),
        InlineKeyboardButton(text="💵 1000 руб.", callback_data="topup:1000"),
    )
    builder.row(
        InlineKeyboardButton(text="💵 2000 руб.", callback_data="topup:2000"),
        InlineKeyboardButton(text="💵 5000 руб.", callback_data="topup:5000"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="menu:profile"))
    return builder.as_markup()


def topup_method_kb(amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Карта / СБП (FreeKassa)", callback_data=f"topup_fk:{amount}"))
    builder.row(InlineKeyboardButton(text="🏦 СБП (Lava)", callback_data=f"topup_lava:{amount}"))
    builder.row(InlineKeyboardButton(text="💎 TON (CryptoBot)", callback_data=f"topup_ton:{amount}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="profile:topup"))
    return builder.as_markup()


def topup_confirm_kb(amount: int) -> InlineKeyboardMarkup:
    return topup_method_kb(amount)


# ─── REFERRAL ────────────────────────────────────────────────────────────────

def referral_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Вывести заработанное", callback_data="referral:withdraw"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


# ─── SUPPORT ─────────────────────────────────────────────────────────────────

def support_kb(support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧑‍💻 Связаться с оператором", url=f"https://t.me/{support_username}"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


# ─── ADMIN ───────────────────────────────────────────────────────────────────

def admin_order_notify_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Выполнить", callback_data=f"admin_complete:{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_fail:{order_id}"),
    )
    return builder.as_markup()
