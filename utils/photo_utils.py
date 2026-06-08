"""
Утилиты для отправки сообщений с фото. Оптимизированная версия.

Логика:
  - Если сообщение уже фото → edit_caption (только текст, без перезагрузки картинки) — БЫСТРО
  - Если сообщение текстовое → удаляем + send_photo (один раз при старте)
  - Если file_id пустой → fallback на edit_text / answer
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
    # Нет file_id — просто текст
    if not photo_id:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return event.message
        else:
            return await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    if isinstance(event, CallbackQuery):
        msg = event.message

        if msg.photo:
            # Сообщение уже фото — просто меняем подпись, картинку НЕ трогаем
            # Это самый быстрый способ — один лёгкий запрос к Telegram
            try:
                await msg.edit_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                return msg
            except TelegramBadRequest as e:
                logger.warning(f"edit_caption failed: {e}")
                # Fallback: попробуем edit_media если подпись не изменилась
                try:
                    await msg.edit_media(
                        media=InputMediaPhoto(media=photo_id, caption=text, parse_mode=parse_mode),
                        reply_markup=reply_markup,
                    )
                    return msg
                except TelegramBadRequest:
                    pass

        # Текстовое сообщение — удаляем и отправляем фото (только первый раз)
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        return await msg.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

    else:
        # Message (из /start или FSM)
        return await event.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )