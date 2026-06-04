"""
VPN раздел — показ инструкции и управление ключами через HAPP.
Администратор добавляет ключи командой /addvpn или через HAPP API.
Покупка VPN временно отключена — раздел информационный.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from keyboards.inline import vpn_menu_kb, back_to_main_kb, back_button
from lexicons.texts import vpn_menu, VPN_INSTRUCTION

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:vpn")
async def cb_vpn_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        text=vpn_menu(),
        reply_markup=vpn_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "vpn:instruction")
async def cb_vpn_instruction(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        text=VPN_INSTRUCTION,
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vpn:") & ~F.data.in_({"vpn:instruction"}))
async def cb_vpn_coming_soon(callback: CallbackQuery) -> None:
    await callback.answer(
        "🚧 VPN временно недоступен для покупки.\nОбратитесь в поддержку.",
        show_alert=True,
    )
