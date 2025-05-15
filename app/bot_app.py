from aiogram import Bot, Dispatcher
from app.config import settings
from app.utils import setup_logging, get_logger
from app.middlewares import LoggingMiddleware
from app.utils import init_db
from aiogram_dialog import setup_dialogs


class BotApplication:
    """Базовый класс для Telegram-бота."""

    def __init__(self):
        # Настройка логирования
        setup_logging()
        self.logger = get_logger(__name__)

        # Инициализация бота и диспетчера
        self.bot = Bot(token=settings.telegram_token)
        self.dp = Dispatcher()

        # Регистрация middleware
        self.dp.message.middleware(LoggingMiddleware())
        # настройка промежуточных программ и основных обработчиков aiogram-dialogs
        setup_dialogs(self.dp)
        self.logger.info("Бот инициализирован")

    async def start(self):
        await init_db()
        # Очистка накопившихся обновлений
        self.logger.info("Очистка накопившихся обновлений...")
        await self.bot.delete_webhook(drop_pending_updates=True)
        # Пропускаем накопившиеся апдейты и запускаем polling
        self.logger.info("Запуск polling...")
        await self.dp.start_polling(self.bot, skip_updates=True)

    def register_startup(self):
        """Регистрация обработчика запуска."""

        @self.dp.startup()
        async def on_startup():
            self.logger.info("Бот запущен...")
