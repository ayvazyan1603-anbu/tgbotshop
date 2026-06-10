"""Reply keyboard — постоянная кнопка 'Меню' рядом с полем ввода."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def menu_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="☰ Меню")]],
        resize_keyboard=True,
        persistent=True,        # кнопка всегда видна, не скрывается
        input_field_placeholder="Введите сообщение или нажмите Меню...",
    )


def remove_reply_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
