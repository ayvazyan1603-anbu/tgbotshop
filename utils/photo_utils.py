"""
Утилиты для отправки сообщений с фото.

Логика:
  - Если у сообщения уже есть фото (message.photo) → edit_media (меняем фото + текст)
  - Если сообщение текстовое → удаляем его и отправляем send_photo
  - Если file_id пустой → fallback на обычный edit_text / answer
"""
import logging
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def send_or_edit_photo(
    event: Message | CallbackQuery,
    photo_id: str,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> Message:
    """
    Универсальная функция: отправляет или редактирует сообщение с фото.
    Принимает как Message (из команды/FSM), так и CallbackQuery.
    """
    # Нет file_id — просто текст
    if not photo_id:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return event.message
        else:
            return await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    if isinstance(event, CallbackQuery):
        msg = event.message
        # Уже фото — редактируем медиа
        if msg.photo:
            try:
                await msg.edit_media(
                    media=InputMediaPhoto(
                        media=photo_id,
                        caption=text,
                        parse_mode=parse_mode,
                    ),
                    reply_markup=reply_markup,
                )
                return msg
            except TelegramBadRequest as e:
                logger.warning(f"edit_media failed: {e}")
        # Текстовое сообщение — удаляем и шлём фото
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        return await event.message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    else:
        # Message (из FSM или команды) — просто send_photo
        return await event.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )