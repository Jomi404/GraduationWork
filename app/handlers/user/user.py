from aiogram.types import Message
from aiogram.filters import Command
from app.handlers import BaseHandler
from app.keyboards import get_main_keyboard


class UserHandler(BaseHandler):
    """Обработчик команд для пользователей."""

    def register_handlers(self):
        """Регистрация обработчиков для пользователей."""
        self.dp.message(Command("start"))(self.start_command)

    async def start_command(self, message: Message) -> None:
        """Обработчик команды /start. Отправляет приветственное сообщение с клавиатурой."""
        user = message.from_user

        self.logger.info(f"Пользователь {user.id} ({user.first_name}) отправил команду /start")

        welcome_message = (
            f"Привет, {user.first_name}! 👋\n"
            "Я твой чат-бот. Чем могу помочь?"
        )
        keyboard = get_main_keyboard()
        await message.reply(welcome_message, reply_markup=keyboard)
