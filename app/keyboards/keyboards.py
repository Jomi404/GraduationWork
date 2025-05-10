from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram import types


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру для пользователей."""
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text='Помощь'))
    markup = keyboard_builder.as_markup()
    return markup
