import logging
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_edit(
    msg,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    **kwargs,
) -> None:
    """
    Безопасное редактирование сообщения.
    Автоматически выбирает edit_caption (для фото) или edit_text (для текста).
    Игнорирует ошибку «message is not modified».
    """
    try:
        if msg.photo or msg.video or msg.document or msg.animation:
            await msg.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            await msg.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs,
            )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.warning(f"safe_edit failed: {e}")


async def send_or_edit_photo(
    event: Message | CallbackQuery,
    photo_id: str,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    photo_unique_id: str = "",
) -> Message:
    """
    Если photo_unique_id передан — сравниваем с текущим фото:
      - совпадает  → edit_caption (быстро, картинка не трогается)
      - отличается → edit_media   (меняем картинку + текст)
    Если photo_unique_id не передан — всегда edit_media (медленнее но надёжно).
    """
    if not photo_id:
        if isinstance(event, CallbackQuery):
            await safe_edit(event.message, text, reply_markup=reply_markup, parse_mode=parse_mode)
            return event.message
        else:
            return await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    if isinstance(event, CallbackQuery):
        msg = event.message

        if msg.photo:
            current_unique = msg.photo[-1].file_unique_id
            same_photo = photo_unique_id and (current_unique == photo_unique_id)

            if same_photo:
                # Фото не изменилось — меняем только подпись, очень быстро
                try:
                    await msg.edit_caption(
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    )
                    return msg
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        logger.warning(f"edit_caption failed: {e}")
                    return msg
            else:
                # Фото другое — меняем медиа целиком
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
                    if "message is not modified" in str(e):
                        return msg
                    logger.warning(f"edit_media failed: {e}")
                    return msg
        else:
            # Текстовое сообщение — удаляем и отправляем фото
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
        return await event.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
