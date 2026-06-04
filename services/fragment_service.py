"""
Fragment Service — интеграция с iStar API (fragmentapi.com).
Документация: https://istar.fragmentapi.com/docs
Дашборд:      https://v1.fragmentapi.com/partner/dashboard

Флоу покупки Stars:
  1. get_star_recipient()  — валидация получателя, получаем recipient_hash
  2. create_star_order()   — создаём заказ, получаем order_id (статус: pending)
  3. Webhook на /webhook/fragment → меняем статус заказа в БД

Флоу покупки Premium — аналогичный.
"""
import logging
from typing import Optional
from dataclasses import dataclass

import aiohttp

from config import config

logger = logging.getLogger(__name__)

BASE_URL = "https://v1.fragmentapi.com/api/v1/partner"


@dataclass
class RecipientInfo:
    recipient_hash: str
    name: str
    photo: str


@dataclass
class FragmentOrder:
    order_id: str
    status: str       # "pending" | "completed" | "failed"
    amount: float     # в TON


class FragmentAPIError(Exception):
    pass


def _headers() -> dict:
    return {
        "API-Key": config.fragment_api_key,
        "Content-Type": "application/json",
    }


# ─── STARS ───────────────────────────────────────────────────────────────────

async def get_star_recipient(username: str, quantity: int) -> RecipientInfo:
    """
    Валидировать получателя Stars.
    username — без @, например "durov"
    Raises FragmentAPIError при ошибке.
    """
    username = username.lstrip("@")
    url = f"{BASE_URL}/star/recipient/search"
    params = {"username": username, "quantity": quantity}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, params=params, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            if not data.get("success"):
                raise FragmentAPIError(data.get("message", "Recipient not found"))
            return RecipientInfo(
                recipient_hash=data["recipient"],
                name=data.get("name", ""),
                photo=data.get("photo", ""),
            )


async def create_star_order(
    username: str,
    recipient_hash: str,
    quantity: int,
) -> FragmentOrder:
    """
    Создать заказ на отправку Stars.
    Заказ асинхронный — результат придёт в webhook.
    """
    url = f"{BASE_URL}/orders/star"
    payload = {
        "username": username.lstrip("@"),
        "recipient_hash": recipient_hash,
        "quantity": quantity,
        "wallet_type": "TON",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            # 200, 201, 202 — все валидные ответы от iStar (202 = принято асинхронно)
            if resp.status not in (200, 201, 202) or not data.get("order_id"):
                raise FragmentAPIError(
                    data.get("message", f"Order failed: HTTP {resp.status}")
                )
            return FragmentOrder(
                order_id=data["order_id"],
                status=data.get("status", "pending"),
                amount=data.get("amount", 0.0),
            )


# ─── PREMIUM ─────────────────────────────────────────────────────────────────

async def get_premium_recipient(username: str, months: int) -> RecipientInfo:
    """Валидировать получателя Premium."""
    username = username.lstrip("@")
    url = f"{BASE_URL}/premium/recipient/search"
    params = {"username": username, "months": months}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, params=params, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            if not data.get("success"):
                raise FragmentAPIError(data.get("message", "Recipient not found"))
            return RecipientInfo(
                recipient_hash=data["recipient"],
                name=data.get("name", ""),
                photo=data.get("photo", ""),
            )


async def create_premium_order(
    username: str,
    recipient_hash: str,
    months: int,
) -> FragmentOrder:
    """Создать заказ на Premium Gift."""
    url = f"{BASE_URL}/orders/premium"
    payload = {
        "username": username.lstrip("@"),
        "recipient_hash": recipient_hash,
        "months": months,
        "wallet_type": "TON",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201, 202) or not data.get("order_id"):
                raise FragmentAPIError(
                    data.get("message", f"Order failed: HTTP {resp.status}")
                )
            return FragmentOrder(
                order_id=data["order_id"],
                status=data.get("status", "pending"),
                amount=data.get("amount", 0.0),
            )


# ─── WALLET ──────────────────────────────────────────────────────────────────

async def get_wallet_balance() -> float:
    """Получить баланс TON-кошелька в iStar."""
    url = f"{BASE_URL}/wallet/balance"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            data = await resp.json()
            return float(data.get("balance", 0.0))
