import asyncio
from aiogram import Bot, Dispatcher
from app.config import TELEGRAM_TOKEN
from app.utils import setup_logging, get_logger
from app.middlewares import LoggingMiddleware
from app.utils import init_db


class BotApplication:
    """Базовый класс для Telegram-бота."""

    def __init__(self):
        # Настройка логирования
        setup_logging()
        self.logger = get_logger(__name__)

        # Инициализация бота и диспетчера
        self.bot = Bot(token=TELEGRAM_TOKEN)
        self.dp = Dispatcher()

        # Регистрация middleware
        self.dp.message.middleware(LoggingMiddleware())

        self.logger.info("Бот инициализирован")

    async def start(self):
        self.logger.info("Инициализация базы данных...")
        await asyncio.to_thread(init_db)
        """Запуск бота."""
        self.logger.info("Запуск polling...")
        await self.dp.start_polling(self.bot)

    def register_startup(self):
        """Регистрация обработчика запуска."""

        @self.dp.startup()
        async def on_startup():
            self.logger.info("Бот запущен...")
