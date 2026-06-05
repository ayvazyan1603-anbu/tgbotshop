from config import config

# ─── MAIN MENU ───────────────────────────────────────────────────────────────

def main_menu(balance: float) -> str:
    return (
        "🤖 <b>Добро пожаловать в цифровой маркетплейс!</b>\n\n"
        "Здесь вы можете моментально приобрести Telegram Stars, Premium, "
        "уникальные подарки и надёжный VPN, а также заработать на нашей "
        "партнёрской программе.\n\n"
        f"💳 <b>Ваш баланс:</b> {balance:.2f} руб."
    )


# ─── STARS ───────────────────────────────────────────────────────────────────

def stars_menu() -> str:
    return (
        "🌟 <b>Покупка Telegram Stars</b>\n\n"
        "Выберите необходимое количество звёзд для зачисления на ваш аккаунт.\n"
        "Перевод осуществляется по UID или юзернейму."
    )


def stars_enter_username() -> str:
    return (
        "✏️ <b>Введите ваш Telegram юзернейм или UID</b>\n\n"
        "Пример: <code>@username</code> или <code>123456789</code>"
    )


def stars_custom_amount() -> str:
    return (
        "✏️ <b>Введите количество звёзд</b>\n\n"
        "Минимум: <b>50</b> | Максимум: <b>10 000</b>\n"
        "Цена рассчитается автоматически."
    )


def stars_confirm(amount: int, price: float, recipient: str) -> str:
    return (
        f"⭐ <b>Подтверждение покупки Stars</b>\n\n"
        f"Количество: <b>{amount} Stars</b>\n"
        f"Получатель: <code>{recipient}</code>\n"
        f"Стоимость: <b>{price:.2f} руб.</b>\n\n"
        "Подтвердите покупку. Средства будут списаны с вашего баланса."
    )


# ─── PREMIUM ─────────────────────────────────────────────────────────────────

def premium_menu() -> str:
    return (
        "💎 <b>Telegram Premium подписка</b>\n\n"
        "Активация подписки Premium в виде подарка на ваш аккаунт или по ссылке-гифту.\n"
        "Выберите срок действия:"
    )


def premium_enter_username() -> str:
    return (
        "✏️ <b>Введите ваш Telegram юзернейм или UID</b>\n\n"
        "Пример: <code>@username</code> или <code>123456789</code>"
    )


def premium_confirm(months: int, price: float, recipient: str) -> str:
    return (
        f"💎 <b>Подтверждение покупки Premium</b>\n\n"
        f"Срок: <b>{months} мес.</b>\n"
        f"Получатель: <code>{recipient}</code>\n"
        f"Стоимость: <b>{price:.2f} руб.</b>\n\n"
        "Подтвердите покупку. Средства будут списаны с вашего баланса."
    )


# ─── GIFTS ───────────────────────────────────────────────────────────────────

def gifts_menu() -> str:
    return (
        "🎁 <b>Магазин Telegram Подарков</b>\n\n"
        "Вы можете приобрести удалённые подарки для демонстрации в профиле."
    )


def gift_confirm(gift_name: str, price: float, recipient: str) -> str:
    return (
        f"🎁 <b>Подтверждение покупки подарка</b>\n\n"
        f"Подарок: <b>{gift_name}</b>\n"
        f"Получатель: <code>{recipient}</code>\n"
        f"Стоимость: <b>{price:.2f} руб.</b>\n\n"
        "Подтвердите покупку."
    )


def gift_enter_recipient() -> str:
    return (
        "✏️ <b>Введите получателя подарка</b>\n\n"
        "Укажите юзернейм: <code>@username</code> или UID: <code>123456789</code>"
    )


# ─── VPN ─────────────────────────────────────────────────────────────────────

def vpn_menu() -> str:
    return (
        "🌐 <b>Высокоскоростной VPN</b>\n"
        "<i>Протокол VLESS / Shadowsocks</i>\n\n"
        "✅ Стабильное подключение\n"
        "✅ Без ограничений по трафику\n"
        "✅ Все устройства: iOS, Android, Windows, macOS\n\n"
        "Выберите срок подписки:"
    )


def vpn_confirm(months: int, price: float) -> str:
    return (
        f"🌐 <b>Подтверждение покупки VPN</b>\n\n"
        f"Срок: <b>{months} мес.</b>\n"
        f"Стоимость: <b>{price:.2f} руб.</b>\n\n"
        "Ключ будет выдан автоматически после оплаты."
    )


VPN_INSTRUCTION = (
    "📱 <b>Инструкция по настройке VPN</b>\n\n"
    "<b>1. Установите приложение:</b>\n"
    "• iOS/macOS: <a href='https://apps.apple.com/app/streisand/id6450534064'>Streisand</a>\n"
    "• Android: <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>v2rayNG</a>\n"
    "• Windows: <a href='https://github.com/2dust/v2rayN/releases'>v2rayN</a>\n\n"
    "<b>2. Добавьте ключ:</b>\n"
    "Скопируйте ключ из бота → нажмите «Добавить» в приложении → вставьте.\n\n"
    "<b>3. Подключитесь</b> и пользуйтесь! 🚀"
)


# ─── PROFILE ─────────────────────────────────────────────────────────────────

def profile_text(
    user_id: int,
    reg_date: str,
    balance: float,
    total_orders: int,
) -> str:
    return (
        "👤 <b>Ваш личный кабинет</b>\n\n"
        f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n"
        f"📅 <b>Дата регистрации:</b> {reg_date}\n"
        f"💳 <b>Текущий баланс:</b> {balance:.2f} руб.\n"
        f"🛒 <b>Всего покупок:</b> {total_orders} шт."
    )


def topup_text() -> str:
    return (
        "💳 <b>Пополнение баланса</b>\n\n"
        "Введите сумму пополнения в чат (в рублях) или выберите готовый вариант ниже.\n"
        "Оплата принимается автоматически."
    )


def topup_invoice(amount: float) -> str:
    return (
        f"💳 <b>Пополнение на {amount:.0f} руб.</b>\n\n"
        "Нажмите кнопку ниже для перехода к оплате."
    )


# ─── ORDERS HISTORY ──────────────────────────────────────────────────────────

ITEM_TYPE_NAMES = {
    "stars": "⭐ Telegram Stars",
    "premium": "💎 Telegram Premium",
    "gift_regular": "🎁 Удалённые подарки",
    "gift_special": "✨ Особенный подарок",
    "vpn": "🌐 VPN",
    "balance": "💳 Пополнение баланса",
}

STATUS_NAMES = {
    "pending": "⏳ В обработке",
    "completed": "✅ Выполнен",
    "failed": "❌ Ошибка",
    "refunded": "↩️ Возврат",
}


def orders_history(orders: list) -> str:
    if not orders:
        return "📜 <b>История покупок</b>\n\n<i>У вас ещё нет покупок.</i>"
    lines = ["📜 <b>История покупок</b> (последние 20)\n"]
    for o in orders:
        name = ITEM_TYPE_NAMES.get(o.item_type, o.item_type)
        status = STATUS_NAMES.get(o.status, o.status)
        date = o.created_at.strftime("%d.%m.%Y %H:%M")
        lines.append(
            f"#{o.id} | {name}\n"
            f"   💰 {o.price:.2f} руб. | {status}\n"
            f"   📅 {date}\n"
        )
    return "\n".join(lines)


# ─── REFERRAL ────────────────────────────────────────────────────────────────

def referral_text(
    bot_username: str,
    user_id: int,
    ref_count: int,
    ref_earned: float,
) -> str:
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    return (
        "🤝 <b>Партнёрская программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>{config.referral_percent}%</b> "
        "от каждого их пополнения баланса!\n"
        "Вы можете выводить заработанные средства или тратить их внутри бота.\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n"
        "📊 <b>Статистика:</b>\n"
        f"• Приглашено пользователей: <b>{ref_count}</b> чел.\n"
        f"• Заработано всего: <b>{ref_earned:.2f}</b> руб."
    )


# ─── SUPPORT ─────────────────────────────────────────────────────────────────

def support_text() -> str:
    return (
        "🆘 <b>Служба поддержки пользователей</b>\n\n"
        "Возникли проблемы с оплатой, не пришёл товар или не работает VPN?\n"
        "Наш менеджер поможет вам решить любой вопрос.\n\n"
        "⏰ <b>График работы:</b> с 09:00 до 23:00 по МСК."
    )


# ─── SYSTEM MESSAGES ─────────────────────────────────────────────────────────

NOT_ENOUGH_BALANCE = (
    "❌ <b>Недостаточно средств на балансе!</b>\n\n"
    "Пополните баланс в разделе «Профиль → Пополнить баланс»."
)

PURCHASE_SUCCESS = "✅ <b>Покупка успешно выполнена!</b>"

PURCHASE_FAILED = (
    "❌ <b>Ошибка при обработке покупки.</b>\n\n"
    "Пожалуйста, обратитесь в поддержку, если средства были списаны."
)

BALANCE_UPDATED = lambda amount, new_bal: (
    f"✅ <b>Баланс пополнен на {amount:.2f} руб.</b>\n"
    f"Текущий баланс: <b>{new_bal:.2f} руб.</b>"
)

INVALID_AMOUNT = "❌ Введите корректную сумму (целое число, минимум 10 руб.)"

INVALID_STARS_AMOUNT = "❌ Введите количество звёзд (от 50 до 10 000)"

WITHDRAWAL_REQUEST = lambda amount: (
    f"📤 <b>Заявка на вывод {amount:.2f} руб. принята.</b>\n\n"
    "Менеджер обработает запрос в течение 24 часов."
)

VPN_KEY_DELIVERED = lambda key, expires: (
    f"🌐 <b>Ваш VPN ключ:</b>\n\n"
    f"<code>{key}</code>\n\n"
    f"📅 <b>Действителен до:</b> {expires}\n\n"
    "ℹ️ Нажмите на ключ, чтобы скопировать. "
    "Инструкция по настройке в разделе VPN."
)

NO_VPN_KEYS = (
    "⚠️ <b>К сожалению, VPN ключи для данного периода временно недоступны.</b>\n\n"
    "Пожалуйста, обратитесь в поддержку или попробуйте позже."
)

STARS_ORDER_PLACED = lambda amount, recipient: (
    f"✅ <b>Заявка на {amount} Stars принята!</b>\n\n"
    f"Получатель: <code>{recipient}</code>\n\n"
    "Звёзды будут зачислены в течение нескольких минут.\n"
    "Если Stars не пришли через 30 минут — обратитесь в поддержку."
)

PREMIUM_ORDER_PLACED = lambda months, recipient: (
    f"✅ <b>Заявка на Premium {months} мес. принята!</b>\n\n"
    f"Получатель: <code>{recipient}</code>\n\n"
    "Подписка будет активирована в течение нескольких минут."
)
