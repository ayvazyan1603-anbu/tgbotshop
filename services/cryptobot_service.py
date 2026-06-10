"""
CryptoBot — оплата в TON через @CryptoBot.
Документация: https://help.crypt.bot/crypto-pay-api
Получить токен: @CryptoBot → /pay → Create App
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass

import aiohttp

from config import config

logger = logging.getLogger(__name__)

BASE_URL = "https://pay.crypt.bot/api"


@dataclass
class CryptoBotInvoice:
    invoice_id: int
    url: str
    amount: float
    currency: str


async def register_webhook(app_url: str) -> bool:
    """
    Регистрирует вебхук в CryptoBot.
    Вызывается один раз при старте бота.
    app_url — публичный URL Railway (например https://yourapp.up.railway.app)
    """
    webhook_url = f"{app_url.rstrip('/')}/webhook/cryptobot"
    headers = {"Crypto-Pay-API-Token": config.cryptobot_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/setWebhook",
            params={"url": webhook_url},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            data = await resp.json()
            if data.get("ok"):
                logger.info(f"CryptoBot webhook registered: {webhook_url}")
                return True
            else:
                logger.error(f"CryptoBot setWebhook failed: {data}")
                return False


async def create_invoice(amount_rub: float, user_id: int) -> CryptoBotInvoice:
    ton_amount = await _rub_to_ton(amount_rub)
    payload = {
        "asset": "TON",
        "amount": str(round(ton_amount, 4)),
        "description": f"Пополнение баланса на {amount_rub:.0f} руб.",
        "payload": f"topup:{user_id}:{amount_rub:.0f}",
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 1800,
    }
    headers = {"Crypto-Pay-API-Token": config.cryptobot_token, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/createInvoice", json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            data = await resp.json()
            if not data.get("ok"):
                err = data.get("error", {})
                raise ValueError(err.get("name", f"CryptoBot error: {data}"))
            inv = data["result"]
            return CryptoBotInvoice(
                invoice_id=inv["invoice_id"],
                url=inv["bot_invoice_url"],
                amount=ton_amount,
                currency="TON",
            )


async def _rub_to_ton(rub_amount: float) -> float:
    try:
        headers = {"Crypto-Pay-API-Token": config.cryptobot_token}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/getExchangeRates", headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    for rate in data["result"]:
                        if rate["source"] == "TON" and rate["target"] == "RUB":
                            return round(rub_amount / float(rate["rate"]), 4)
    except Exception as e:
        logger.error(f"Exchange rate error: {e}")
    return round(rub_amount / 600, 4)  # fallback


def verify_cryptobot_webhook(body: bytes, signature: str) -> bool:
    if not config.cryptobot_token:
        return True
    secret = hashlib.sha256(config.cryptobot_token.encode()).digest()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
