import asyncio
from app import BotApplication, UserHandler, AdminHandler


async def main():
    app = BotApplication()

    UserHandler(app.dp)
    AdminHandler(app.dp)

    app.register_startup()

    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
