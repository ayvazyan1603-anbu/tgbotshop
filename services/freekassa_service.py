"""
FreeKassa — платёжный сервис (банковские карты, СБП, электронные кошельки).
Документация: https://docs.freekassa.net

Флоу:
  1. create_invoice()  — формируем ссылку на оплату с подписью
  2. Пользователь переходит и платит
  3. FreeKassa отправляет POST-вебхук → проверяем подпись → зачисляем баланс
"""
import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from config import config

logger = logging.getLogger(__name__)

PAYMENT_URL = "https://pay.freekassa.net/"
API_BASE    = "https://api.freekassa.net/v1"


@dataclass
class FreekassaInvoice:
    order_id: str
    url: str
    amount: float


def _sign_form(shop_id: str, amount: float, secret1: str, currency: str, order_id: str) -> str:
    """Подпись для формы оплаты: MD5(shop_id:amount:secret1:currency:order_id)."""
    raw = f"{shop_id}:{amount:.2f}:{secret1}:{currency}:{order_id}"
    return hashlib.md5(raw.encode()).hexdigest()


def _sign_api(params: dict, secret: str) -> str:
    """Подпись для API-запросов: HMAC-SHA256(sorted_values, secret)."""
    values = "|".join(str(params[k]) for k in sorted(params))
    return hmac.new(secret.encode(), values.encode(), hashlib.sha256).hexdigest()


async def create_invoice(
    amount: float,
    user_id: int,
    currency: str = "RUB",
    comment: str = "Пополнение баланса",
) -> FreekassaInvoice:
    """
    Сформировать ссылку на оплату через FreeKassa.
    Возвращает FreekassaInvoice с URL для редиректа пользователя.
    """
    shop_id  = config.freekassa_shop_id
    secret1  = config.freekassa_secret1
    order_id = f"topup_{user_id}_{uuid.uuid4().hex[:8]}"

    sign = _sign_form(shop_id, amount, secret1, currency, order_id)

    params = {
        "m":          shop_id,
        "oa":         f"{amount:.2f}",
        "currency":   currency,
        "o":          order_id,
        "s":          sign,
        "us_user_id": str(user_id),       # передаём user_id в вебхук
        "lang":       "ru",
        "i":          "",                  # пустая строка = все методы
    }
    url = PAYMENT_URL + "?" + urlencode(params)

    return FreekassaInvoice(order_id=order_id, url=url, amount=amount)


def verify_freekassa_webhook(
    shop_id: str,
    amount: str,
    order_id: str,
    received_sign: str,
) -> bool:
    """
    Проверить подпись входящего уведомления от FreeKassa.
    FreeKassa присылает: MERCHANT_ID, AMOUNT, intid, MERCHANT_ORDER_ID, P_EMAIL, P_PHONE,
                         CUR_ID, SIGN (MD5(shop_id:amount:secret2:order_id))
    """
    secret2 = config.freekassa_secret2
    expected = hashlib.md5(
        f"{shop_id}:{amount}:{secret2}:{order_id}".encode()
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), received_sign.lower())


async def get_order_status(order_id: str) -> Optional[str]:
    """
    Проверить статус заказа через API FreeKassa.
    Возвращает 'success', 'pending', 'canceled' или None при ошибке.
    """
    api_key  = config.freekassa_api_key
    shop_id  = config.freekassa_shop_id
    nonce    = str(uuid.uuid4().int)[:15]

    params = {
        "shopId":  shop_id,
        "nonce":   nonce,
        "orderId": order_id,
    }
    params["signature"] = _sign_api(params, api_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/orders",
                json=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                if data.get("type") == "success" and data.get("orders"):
                    return data["orders"][0].get("status")
    except Exception as e:
        logger.error(f"FreeKassa API error: {e}")
    return None
