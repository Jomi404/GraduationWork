from aiogram.types import Message
from aiogram.filters import Command
from app.handlers import BaseHandler


class AdminHandler(BaseHandler):
    """Обработчик команд для администраторов."""

    def register_handlers(self):
        """Регистрация обработчиков для администраторов."""
        self.dp.message(Command("admin"))(self.admin_command)

    async def admin_command(self, message: Message) -> None:
        """Обработчик команды /admin."""
        self.logger.info(f"Пользователь {message.from_user.id} вызвал команду /admin")
        await message.reply("Это команда для администратора.")