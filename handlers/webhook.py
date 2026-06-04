"""
Единый вебхук-сервер для всех платёжных систем:
  POST /webhook/fragment   — iStar (доставка Stars/Premium)
  POST /webhook/lava       — Lava.ru (пополнение через СБП)
  POST /webhook/cryptobot  — CryptoBot (пополнение через TON)
"""
import hashlib
import hmac
import json
import logging

from aiohttp import web
from aiogram import Bot

from config import config
from database.engine import async_session_factory
from database.models import Order, OrderStatus
from keyboards.inline import main_menu_kb
from services.lava_service import verify_lava_webhook
from services.cryptobot_service import verify_cryptobot_webhook

logger = logging.getLogger(__name__)


# ─── FRAGMENT WEBHOOK ────────────────────────────────────────────────────────

async def fragment_webhook_handler(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    body = await request.read()

    signature = request.headers.get("X-iStar-Signature", "")
    if config.fragment_webhook_secret:
        expected = hmac.new(
            config.fragment_webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return web.Response(status=403, text="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    event_type = payload.get("event_type")
    order_data = payload.get("order", {})
    fragment_order_id = order_data.get("id")

    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Order).where(Order.delivery_data == fragment_order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return web.Response(status=200, text="OK")

        if event_type == "order.completed":
            order.status = OrderStatus.COMPLETED
            await session.commit()
            try:
                await bot.send_message(
                    chat_id=order.user_id,
                    text=f"✅ <b>Заказ #{order.id} выполнен!</b>\n\n{order.item_detail}\n\nСпасибо за покупку! 🎉",
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Notify error: {e}")

        elif event_type == "order.failed":
            order.status = OrderStatus.FAILED
            await session.commit()
            from database.repo import update_balance
            await update_balance(
                session, order.user_id, order.price,
                "refund", f"Возврат по заказу #{order.id}"
            )
            try:
                await bot.send_message(
                    chat_id=order.user_id,
                    text=(
                        f"❌ <b>Ошибка доставки по заказу #{order.id}</b>\n\n"
                        f"💳 <b>{order.price:.2f} руб. возвращены на баланс.</b>"
                    ),
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Notify error: {e}")

    return web.Response(status=200, text="OK")


# ─── LAVA WEBHOOK ────────────────────────────────────────────────────────────

async def lava_webhook_handler(request: web.Request) -> web.Response:
    """
    Lava.ru отправляет POST с JSON при успешной оплате.
    Поля: id, order_id, status, amount, custom_fields (наш user_id)
    """
    bot: Bot = request.app["bot"]
    body = await request.read()

    signature = request.headers.get("Signature", "")
    if not verify_lava_webhook(body, signature):
        logger.warning("Invalid Lava webhook signature")
        return web.Response(status=403, text="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    status = payload.get("status")
    if status != "success":
        return web.Response(status=200, text="OK")  # игнорируем не-успешные

    try:
        amount = float(payload.get("amount", 0))
        user_id = int(payload.get("custom_fields", 0))
        if not user_id or amount <= 0:
            raise ValueError("Missing user_id or amount")
    except (ValueError, TypeError) as e:
        logger.error(f"Lava webhook parse error: {e} | payload: {payload}")
        return web.Response(status=200, text="OK")

    async with async_session_factory() as session:
        from services.payment_service import credit_balance
        new_balance = await credit_balance(
            session=session,
            user_id=user_id,
            amount=amount,
            description=f"Пополнение через СБП (Lava) {amount:.2f} руб.",
        )
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Баланс пополнен через СБП!</b>\n\n"
                    f"Сумма: <b>+{amount:.2f} руб.</b>\n"
                    f"Текущий баланс: <b>{new_balance:.2f} руб.</b>"
                ),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Notify error: {e}")

    return web.Response(status=200, text="OK")


# ─── CRYPTOBOT WEBHOOK ───────────────────────────────────────────────────────

async def cryptobot_webhook_handler(request: web.Request) -> web.Response:
    """
    CryptoBot отправляет POST при оплате инвойса.
    Поле payload содержит наш "topup:{user_id}:{amount_rub}"
    """
    bot: Bot = request.app["bot"]
    body = await request.read()

    signature = request.headers.get("crypto-pay-api-signature", "")
    if not verify_cryptobot_webhook(body, signature):
        logger.warning("Invalid CryptoBot webhook signature")
        return web.Response(status=403, text="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    if payload.get("update_type") != "invoice_paid":
        return web.Response(status=200, text="OK")

    invoice = payload.get("payload", {})
    custom_payload = invoice.get("payload", "")  # "topup:{user_id}:{amount_rub}"

    try:
        _, uid_str, amount_str = custom_payload.split(":")
        user_id = int(uid_str)
        amount_rub = float(amount_str)
    except Exception as e:
        logger.error(f"CryptoBot payload parse error: {e}")
        return web.Response(status=200, text="OK")

    async with async_session_factory() as session:
        from services.payment_service import credit_balance
        new_balance = await credit_balance(
            session=session,
            user_id=user_id,
            amount=amount_rub,
            description=f"Пополнение через TON (CryptoBot) {amount_rub:.2f} руб.",
        )
        ton_amount = invoice.get("amount", "?")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Баланс пополнен через TON!</b>\n\n"
                    f"Оплачено: <b>{ton_amount} TON</b>\n"
                    f"Зачислено: <b>+{amount_rub:.2f} руб.</b>\n"
                    f"Текущий баланс: <b>{new_balance:.2f} руб.</b>"
                ),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Notify error: {e}")

    return web.Response(status=200, text="OK")


# ─── LAVA DOMAIN VERIFICATION ────────────────────────────────────────────────

async def lava_verify_handler(request: web.Request) -> web.Response:
    return web.Response(status=200, text=config.lava_verify_code, content_type="text/plain")


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

async def health_handler(request: web.Request) -> web.Response:
    return web.Response(status=200, text="OK")


# ─── APP FACTORY ─────────────────────────────────────────────────────────────

def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/",             health_handler)
    app.router.add_get("/health",       health_handler)
    app.router.add_get("/lava-verify",  lava_verify_handler)
    app.router.add_post("/webhook/fragment",  fragment_webhook_handler)
    app.router.add_post("/webhook/lava",      lava_webhook_handler)
    app.router.add_post("/webhook/cryptobot", cryptobot_webhook_handler)
    return app