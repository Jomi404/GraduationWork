import asyncio
from app import BotApplication
from app.utils import setup_logging, get_logger

async def main():
    # Настройка логирования
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Инициализация приложения...")

    try:
        # Создание и настройка приложения
        logger.debug("Создание экземпляра BotApplication")
        app_main = BotApplication()

        # Регистрация startup-обработчика
        logger.debug("Регистрация startup-обработчика")
        app_main.register_startup()

        # Запуск бота
        logger.info("Запуск бота...")
        await app_main.start()

    except Exception as err:
        logger.error(f"Ошибка при запуске приложения: {str(err)}", exc_info=True)
        raise

    finally:
        logger.info("Завершение работы приложения")
        if 'app_main' in locals():
            await app_main.bot.session.close()
            logger.debug("Сессия бота закрыта")

if __name__ == "__main__":
    my_logger = get_logger(__name__)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        my_logger.info("Приложение остановлено пользователем")
    except Exception as err:
        my_logger.error(f"Критическая ошибка: {str(err)}", exc_info=True)
        raise
