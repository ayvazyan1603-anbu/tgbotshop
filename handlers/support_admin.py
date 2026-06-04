import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo
from database.models import OrderStatus
from keyboards.inline import support_kb, main_menu_kb, admin_order_notify_kb
from lexicons.texts import support_text

logger = logging.getLogger(__name__)
router = Router()


# ─── SUPPORT ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:support")
async def cb_support(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        text=support_text(),
        reply_markup=support_kb(config.support_username),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── ADMIN: COMPLETE ORDER ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_complete:"))
async def cb_admin_complete(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.from_user.id != config.admin_id:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    from sqlalchemy import select
    from database.models import Order
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    order.status = OrderStatus.COMPLETED
    await session.commit()
    try:
        await bot.send_message(
            chat_id=order.user_id,
            text=f"✅ <b>Заказ #{order.id} выполнен!</b>\n\n{order.item_detail}\n\nСпасибо за покупку! 🎉",
            reply_markup=main_menu_kb(), parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Notify error: {e}")
    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ВЫПОЛНЕН</b>", parse_mode="HTML")
    await callback.answer("✅ Выполнен")


# ─── ADMIN: FAIL ORDER ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_fail:"))
async def cb_admin_fail(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.from_user.id != config.admin_id:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    from sqlalchemy import select
    from database.models import Order
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    from services.payment_service import refund_purchase
    await refund_purchase(session, order_id, order.user_id, order.price)
    try:
        await bot.send_message(
            chat_id=order.user_id,
            text=(
                f"↩️ <b>Заказ #{order.id} отменён.</b>\n\n"
                f"💳 <b>{order.price:.2f} руб. возвращены на баланс.</b>"
            ),
            reply_markup=main_menu_kb(), parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Notify error: {e}")
    await callback.message.edit_text(callback.message.text + "\n\n❌ <b>ОТКЛОНЁН — возврат выполнен</b>", parse_mode="HTML")
    await callback.answer("↩️ Отклонён")


# ─── ADMIN COMMANDS ──────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != config.admin_id:
        return
    from sqlalchemy import select, func
    from database.models import Order, User
    user_count = (await session.execute(select(func.count(User.id)))).scalar_one()
    order_count = (await session.execute(select(func.count(Order.id)))).scalar_one()
    pending = (await session.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
    )).scalar_one()
    await message.answer(
        f"⚙️ <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: <b>{user_count}</b>\n"
        f"🛒 Заказов всего: <b>{order_count}</b>\n"
        f"⏳ Ожидают обработки: <b>{pending}</b>\n\n"
        f"<b>Команды:</b>\n"
        f"/addvpn [ключ] [дней] — добавить VPN ключ (HAPP)\n"
        f"/addgift [название] [цена] [regular|special] — добавить подарок\n"
        f"/editgift [id] [цена] — изменить цену подарка\n"
        f"/listgifts — список всех подарков\n"
        f"/fbalance — баланс Fragment (TON)\n"
        f"/broadcast [текст] — рассылка всем",
        parse_mode="HTML",
    )


@router.message(Command("addvpn"))
async def cmd_add_vpn(message: Message, session: AsyncSession) -> None:
    """
    Добавить VPN ключ от HAPP или любой другой панели.
    Формат: /addvpn [ключ] [дней]
    Пример: /addvpn vless://abc123... 30
    """
    if message.from_user.id != config.admin_id:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Формат: /addvpn [ключ] [дней]\n"
            "Пример: /addvpn vless://... 30\n\n"
            "Ключи берёте из панели HAPP или любой другой (Marzban, 3x-UI)."
        )
        return
    key = parts[1]
    try:
        days = int(parts[2])
    except ValueError:
        await message.answer("❌ Некорректное число дней")
        return
    vpn_key = await repo.add_vpn_key(session, key, "vless", days)
    await message.answer(f"✅ VPN ключ добавлен\nID: {vpn_key.id} | {days} дней")


@router.message(Command("addgift"))
async def cmd_add_gift(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != config.admin_id:
        return
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Формат: /addgift [название] [цена] [regular|special]")
        return
    gift_type = parts[-1]
    if gift_type not in ("regular", "special"):
        await message.answer("❌ Тип должен быть: regular или special")
        return
    try:
        price = float(parts[-2])
    except ValueError:
        await message.answer("❌ Некорректная цена")
        return
    name = " ".join(parts[1:-2])
    from database.models import Gift
    gift = Gift(name=name, price=price, gift_type=gift_type, is_available=True, stock=-1)
    session.add(gift)
    await session.commit()
    await message.answer(f"✅ Подарок добавлен\n«{name}» | {price} руб. | {gift_type}")


@router.message(Command("editgift"))
async def cmd_edit_gift(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != config.admin_id:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Формат: /editgift [id] [новая_цена]")
        return
    try:
        gift_id = int(parts[1])
        new_price = float(parts[2])
    except ValueError:
        await message.answer("❌ Некорректные параметры")
        return
    gift = await repo.get_gift(session, gift_id)
    if not gift:
        await message.answer("❌ Подарок не найден")
        return
    gift.price = new_price
    await session.commit()
    await message.answer(f"✅ Цена подарка #{gift_id} «{gift.name}» обновлена: {new_price} руб.")


@router.message(Command("listgifts"))
async def cmd_list_gifts(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != config.admin_id:
        return
    from sqlalchemy import select
    from database.models import Gift
    gifts = (await session.execute(select(Gift).order_by(Gift.gift_type, Gift.id))).scalars().all()
    if not gifts:
        await message.answer("Подарков нет.")
        return
    lines = ["📦 <b>Список подарков:</b>\n"]
    for g in gifts:
        status = "✅" if g.is_available else "❌"
        lines.append(f"{status} #{g.id} | {g.name} | {g.price:.0f} руб. | {g.gift_type}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("fbalance"))
async def cmd_fragment_balance(message: Message) -> None:
    if message.from_user.id != config.admin_id:
        return
    if not config.fragment_api_key:
        await message.answer("❌ FRAGMENT_API_KEY не настроен")
        return
    try:
        from services.fragment_service import get_wallet_balance
        balance = await get_wallet_balance()
        await message.answer(f"💎 <b>Баланс Fragment:</b> <b>{balance:.4f} TON</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, session: AsyncSession, bot: Bot) -> None:
    if message.from_user.id != config.admin_id:
        return
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Формат: /broadcast [текст]")
        return
    broadcast_text = text[1]
    from sqlalchemy import select
    from database.models import User
    users = (await session.execute(select(User.id))).scalars().all()
    sent, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, broadcast_text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📢 Рассылка завершена: ✅ {sent} / ❌ {failed}")
