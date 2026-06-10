import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database import repo
from keyboards.inline import main_menu_kb
from keyboards.reply import menu_reply_kb
from lexicons.texts import main_menu
from utils.photo_utils import send_or_edit_photo
from config import config

logger = logging.getLogger(__name__)
router = Router()


async def _parse_referrer(start_param: str | None) -> int | None:
    if not start_param:
        return None
    if start_param.startswith("ref"):
        try:
            return int(start_param[3:])
        except ValueError:
            return None
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    start_param = message.text.split()[-1] if len(message.text.split()) > 1 else None
    referrer_id = await _parse_referrer(start_param)

    user, is_new = await repo.get_or_create_user(
        session=session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referrer_id=referrer_id,
    )

    if is_new and referrer_id:
        logger.info(f"New user {message.from_user.id} registered via referral of {referrer_id}")

    # Показываем Reply Keyboard с кнопкой Меню (один раз при /start)
    await message.answer("👋 Добро пожаловать!", reply_markup=menu_reply_kb())

    await send_or_edit_photo(
        event=message,
        photo_id=config.photo_id_main,
        photo_unique_id=config.photo_unique_id_main,
        text=main_menu(user.balance),
        reply_markup=main_menu_kb(),
    )


# ─── Reply кнопка «☰ Меню» ───────────────────────────────────────────────────

@router.message(F.text == "☰ Меню")
async def reply_menu_button(message: Message, session: AsyncSession) -> None:
    """Нажатие на постоянную кнопку Меню внизу экрана."""
    user = await repo.get_user(session, message.from_user.id)
    balance = user.balance if user else 0.0
    await send_or_edit_photo(
        event=message,
        photo_id=config.photo_id_main,
        photo_unique_id=config.photo_unique_id_main,
        text=main_menu(balance),
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await repo.get_user(session, callback.from_user.id)
    balance = user.balance if user else 0.0
    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_main,
        photo_unique_id=config.photo_unique_id_main,
        text=main_menu(balance),
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:start")
async def cb_menu_start(callback: CallbackQuery, session: AsyncSession) -> None:
    user, _ = await repo.get_or_create_user(
        session=session,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
        referrer_id=None,
    )
    await send_or_edit_photo(
        event=callback,
        photo_id=config.photo_id_main,
        photo_unique_id=config.photo_unique_id_main,
        text=main_menu(user.balance),
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
