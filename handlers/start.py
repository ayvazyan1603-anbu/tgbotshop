import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database import repo
from keyboards.inline import main_menu_kb, back_to_main_kb
from lexicons.texts import main_menu

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
    # Parse referral
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
        logger.info(
            f"New user {message.from_user.id} registered via referral of {referrer_id}"
        )

    await message.answer(
        text=main_menu(user.balance),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await repo.get_user(session, callback.from_user.id)
    balance = user.balance if user else 0.0
    await callback.message.edit_text(
        text=main_menu(balance),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
