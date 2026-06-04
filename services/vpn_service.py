"""
VPN Service — интеграция с панелью Marzban (или 3X-UI).
Документация Marzban API: https://github.com/Gozargah/Marzban
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp

from config import config

logger = logging.getLogger(__name__)

_marzban_token: Optional[str] = None
_token_expires: Optional[datetime] = None


async def _get_marzban_token() -> Optional[str]:
    """Получить Bearer-токен для Marzban API."""
    global _marzban_token, _token_expires

    if _marzban_token and _token_expires and datetime.utcnow() < _token_expires:
        return _marzban_token

    if not config.marzban_url:
        logger.warning("Marzban URL not configured")
        return None

    url = f"{config.marzban_url}/api/admin/token"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data={
                    "username": config.marzban_username,
                    "password": config.marzban_password,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _marzban_token = data.get("access_token")
                    _token_expires = datetime.utcnow() + timedelta(minutes=55)
                    return _marzban_token
                else:
                    logger.error(f"Marzban auth failed: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Marzban connection error: {e}")
        return None


async def create_vpn_user(user_id: int, duration_days: int) -> Optional[str]:
    """
    Создать VPN пользователя в Marzban.
    Возвращает VLESS-ключ или None при ошибке.
    """
    token = await _get_marzban_token()
    if not token:
        logger.warning("No Marzban token, using fallback key generation")
        return _generate_fallback_key(user_id, duration_days)

    username = f"tgshop_{user_id}_{int(datetime.utcnow().timestamp())}"
    expire_ts = int((datetime.utcnow() + timedelta(days=duration_days)).timestamp())

    payload = {
        "username": username,
        "proxies": {
            "vless": {"flow": "xtls-rprx-vision"},
        },
        "inbounds": {"vless": ["VLESS TCP REALITY"]},
        "expire": expire_ts,
        "data_limit": 0,  # 0 = unlimited
        "data_limit_reset_strategy": "no_reset",
    }

    url = f"{config.marzban_url}/api/user"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    links = data.get("links", [])
                    vless_links = [l for l in links if l.startswith("vless://")]
                    if vless_links:
                        return vless_links[0]
                    # fallback to any link
                    return links[0] if links else None
                else:
                    body = await resp.text()
                    logger.error(f"Marzban create user failed {resp.status}: {body}")
                    return None
    except Exception as e:
        logger.error(f"Marzban create user error: {e}")
        return None


async def delete_vpn_user(username: str) -> bool:
    """Удалить VPN пользователя из Marzban."""
    token = await _get_marzban_token()
    if not token:
        return False
    url = f"{config.marzban_url}/api/user/{username}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                return resp.status == 200
    except Exception as e:
        logger.error(f"Marzban delete user error: {e}")
        return False


def _generate_fallback_key(user_id: int, duration_days: int) -> str:
    """
    Резервный генератор ключа (заглушка).
    Замените на реальную генерацию, если Marzban недоступен.
    """
    import uuid
    fake_uuid = str(uuid.uuid4())
    return (
        f"vless://{fake_uuid}@your-server.com:443"
        f"?type=tcp&security=reality&pbk=YOUR_PUBLIC_KEY"
        f"&fp=chrome&sni=google.com&sid=&spx=%2F"
        f"#{user_id}-{duration_days}days"
    )
