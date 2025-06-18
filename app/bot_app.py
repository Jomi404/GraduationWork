from aiogram import Bot, Dispatcher, Router
from aiogram_dialog import setup_dialogs
from app.config import settings
from app.utils import setup_logging, get_logger, generate_default_equipment
from app.middlewares import LoggingMiddleware
from app.utils import init_db
from app.handlers.user.router_user import UserHandler
from app.handlers.admin.router_admin import AdminHandler
from app.core.database import get_session


class BotApplication:
    """Базовый класс для Telegram-бота."""

    def __init__(self):
        setup_logging()
        self.logger = get_logger(__name__)

        self.bot = Bot(token=settings.telegram_token)
        self.dp = Dispatcher()

        self.dp.message.middleware(LoggingMiddleware())

        user_router = Router()
        admin_router = Router()

        self.user_handler = UserHandler(user_router)
        self.admin_handler = AdminHandler(admin_router)

        self.dp.update.middleware(self.user_handler.set_logger_middleware)
        self.dp.update.middleware(self.admin_handler.set_logger_middleware)

        self.user_handler.register_handlers()
        self.admin_handler.register_handlers()

        self.dp.include_router(user_router)
        self.dp.include_router(admin_router)
        setup_dialogs(self.dp)
        self.logger.info("Бот инициализирован")

    async def start(self):
        await init_db()
        async with get_session() as session:
            await generate_default_equipment(session)
        self.logger.info("Очистка накопившихся обновлений...")
        await self.bot.delete_webhook(drop_pending_updates=True)
        self.logger.info("Запуск polling...")
        await self.dp.start_polling(self.bot, skip_updates=True)

    def register_startup(self):
        """Регистрация обработчика запуска."""

        @self.dp.startup()
        async def on_startup():
            self.logger.info("Бот запущен...")
