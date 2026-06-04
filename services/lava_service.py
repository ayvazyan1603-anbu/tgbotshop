"""
Lava.ru — платёжный сервис для СБП и банковских карт.
Документация: https://dev.lava.ru

Флоу:
  1. create_invoice()  — создаём счёт, получаем ссылку на оплату
  2. Пользователь переходит по ссылке и платит через СБП/карту
  3. Lava отправляет вебхук POST на наш сервер → проверяем подпись → зачисляем баланс
"""
import hashlib
import hmac
import json
import logging
import uuid
from typing import Optional
from dataclasses import dataclass

import aiohttp

from config import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lava.ru/business"


@dataclass
class LavaInvoice:
    invoice_id: str
    url: str        # ссылка для оплаты
    amount: float
    expired_at: str


async def create_invoice(
    amount: float,
    user_id: int,
    comment: str = "Пополнение баланса",
) -> LavaInvoice:
    """
    Создать счёт на оплату через Lava.ru.
    Возвращает LavaInvoice с ссылкой для оплаты.
    """
    order_id = f"topup_{user_id}_{uuid.uuid4().hex[:8]}"

    payload = {
        "shopId": config.lava_shop_id,
        "sum": amount,
        "orderId": order_id,
        "comment": comment,
        "customFields": str(user_id),   # передаём user_id для вебхука
        "hookUrl": "",                  # можно задать отдельный вебхук-URL
        "successUrl": "",               # редирект после оплаты (опционально)
        "failUrl": "",
        "expire": 30,                   # срок действия счёта в минутах
        "includeService": ["qr"],       # qr = СБП
    }

    # Подпись: SHA256(json_body + secret_key)
    body_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    signature = hashlib.sha256(
        (body_str + config.lava_secret_key).encode()
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Signature": signature,
        "X-Api-Key": config.lava_api_key,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/invoice/create",
            data=body_str.encode(),
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            if data.get("status") != 1 or not data.get("data"):
                raise ValueError(data.get("error", f"Lava error: HTTP {resp.status}"))
            d = data["data"]
            return LavaInvoice(
                invoice_id=d["id"],
                url=d["url"],
                amount=float(d["amount"]),
                expired_at=d.get("expiredAt", ""),
            )


def verify_lava_webhook(body: bytes, signature: str) -> bool:
    """Проверить подпись входящего вебхука от Lava."""
    if not config.lava_secret_key:
        return True
    expected = hashlib.sha256(
        (body.decode() + config.lava_secret_key).encode()
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
