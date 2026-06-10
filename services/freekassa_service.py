"""
FreeKassa — платёжный сервис (банковские карты, СБП, электронные кошельки).
Документация: https://docs.freekassa.ru

Флоу:
  1. create_invoice()  — формируем ссылку на оплату с подписью
  2. Пользователь переходит и платит
  3. FreeKassa отправляет POST-вебхук → проверяем подпись → зачисляем баланс
"""
import hashlib
import hmac
import logging
import time
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


def _sign_form(shop_id: str, amount: float, secret1: str, order_id: str) -> str:
    """
    Подпись для формы оплаты по документации FreeKassa:
      MD5(shop_id:amount:secret1:order_id)
    Важно: amount передаётся как строка с двумя знаками после запятой.
    """
    raw = f"{shop_id}:{amount:.2f}:{secret1}:{order_id}"
    logger.debug(f"[FREEKASSA] sign raw string: {raw!r}")
    result = hashlib.md5(raw.encode("utf-8")).hexdigest()
    logger.debug(f"[FREEKASSA] sign result: {result}")
    return result


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
    shop_id = config.freekassa_shop_id
    secret1 = config.freekassa_secret1

    # order_id: только цифры и латиница без подчёркиваний — максимальная совместимость
    order_id = f"{int(time.time())}{user_id}"

    logger.info(
        f"[FREEKASSA] Creating invoice | shop_id={shop_id!r} "
        f"amount={amount:.2f} currency={currency} order_id={order_id} user_id={user_id}"
    )
    logger.info(f"[FREEKASSA] secret1 prefix: {secret1[:4]!r}... len={len(secret1)}")

    sign = _sign_form(shop_id, amount, secret1, order_id)

    logger.info(f"[FREEKASSA] Generated sign: {sign}")

    params = {
        "m":          shop_id,
        "oa":         f"{amount:.2f}",
        "currency":   currency,
        "o":          order_id,
        "s":          sign,
        "us_user_id": str(user_id),
        "lang":       "ru",
    }
    url = PAYMENT_URL + "?" + urlencode(params)
    logger.info(f"[FREEKASSA] Payment URL: {url}")

    return FreekassaInvoice(order_id=order_id, url=url, amount=amount)


def verify_freekassa_webhook(
    shop_id: str,
    amount: str,
    order_id: str,
    received_sign: str,
) -> bool:
    """
    Проверить подпись входящего уведомления от FreeKassa.
    MD5(shop_id:amount:secret2:order_id)
    """
    secret2 = config.freekassa_secret2
    raw = f"{shop_id}:{amount}:{secret2}:{order_id}"
    expected = hashlib.md5(raw.encode("utf-8")).hexdigest()
    logger.info(
        f"[FREEKASSA] Webhook sign check | "
        f"raw={raw!r} expected={expected} received={received_sign}"
    )
    return hmac.compare_digest(expected.lower(), received_sign.lower())


async def get_order_status(order_id: str) -> Optional[str]:
    """
    Проверить статус заказа через API FreeKassa.
    Возвращает 'success', 'pending', 'canceled' или None при ошибке.
    """
    api_key = config.freekassa_api_key
    shop_id = config.freekassa_shop_id
    nonce   = str(uuid.uuid4().int)[:15]

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
