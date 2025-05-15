from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Url
from app.handlers import BaseHandler
from app.handlers.admin.utils import AdminFilter


class AdminDialogStates(StatesGroup):
    main = State()
    admin_menu = State()  # State for the admin menu


async def on_admin_panel_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Панель администратора'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = dialog_manager.event.from_user.id
    if logger:
        logger.info(f"Администратор {user_id} нажал 'Панель администратора'")
    # Switch to the new admin menu (URL button is in the menu)
    await dialog_manager.switch_to(AdminDialogStates.admin_menu)


async def on_view_stats_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Посмотреть статистику'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = callback.from_user.id
    if logger:
        logger.info(f"Администратор {user_id} запросил статистику")
    await callback.message.answer("Статистика: 100 пользователей, 50 активных.")


async def on_manage_users_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Управление пользователями'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = callback.from_user.id
    if logger:
        logger.info(f"Администратор {user_id} запросил управление пользователями")
    await callback.message.answer("Управление пользователями: [в разработке].")


async def on_back_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Назад'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = callback.from_user.id
    if logger:
        logger.info(f"Администратор {user_id} вернулся в главное меню")
    await dialog_manager.switch_to(AdminDialogStates.main)


async def on_exit_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Выход'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = callback.from_user.id
    if logger:
        logger.info(f"Администратор {user_id} вышел из админ-меню")
    await callback.message.answer("Админ-меню закрыто. Теперь вам доступна команда /start и другие.")
    await dialog_manager.done()  # Close the dialog to reset state


def admin_dialog() -> Dialog:
    """Создаёт диалог для администраторов."""
    return Dialog(
        Window(
            Const("Добро пожаловать в админ-панель! 👑 Что хотите сделать?"),
            Button(
                text=Const("Панель администратора"),
                id="admin_panel",
                on_click=on_admin_panel_click
            ),
            state=AdminDialogStates.main,
        ),
        Window(
            Const("Выберите действие в админ-панели:"),
            Url(
                text=Const("Перейти в панель администратора"),
                url=Const("https://admin-panel-78o9.onrender.com")
            ),
            Button(
                text=Const("Посмотреть статистику"),
                id="view_stats",
                on_click=on_view_stats_click
            ),
            Button(
                text=Const("Управление пользователями"),
                id="manage_users",
                on_click=on_manage_users_click
            ),
            Button(
                text=Const("Назад"),
                id="back",
                on_click=on_back_click
            ),
            Button(
                text=Const("Выход"),
                id="exit",
                on_click=on_exit_click
            ),
            state=AdminDialogStates.admin_menu,
        )
    )


class AdminHandler(BaseHandler):
    """Обработчик команд для администраторов."""

    def __init__(self, dp):
        self.dialog = admin_dialog()  # Инициализируем диалог до super().__init__
        super().__init__(dp)

    def register_handlers(self):
        """Регистрация обработчиков для администраторов."""
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]), AdminFilter())(self.admin_command)
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]), ~AdminFilter())(self.on_non_admin_access)
        self.dp.include_router(self.dialog)

    async def admin_command(self, message: Message, dialog_manager: DialogManager) -> None:
        """Обработчик команды /admin."""
        user = message.from_user
        self.logger.info(f"Администратор {user.id} ({user.first_name}) вызвал команду /admin")
        dialog_manager.middleware_data["logger"] = self.logger  # Передаем логгер в DialogManager
        await dialog_manager.start(state=AdminDialogStates.main)

    async def on_non_admin_access(self, message: Message) -> None:
        """Обработчик для пользователей, не являющихся администраторами."""
        self.logger.info(f"Пользователь {message.from_user.id} попытался вызвать команду /admin, но не является "
                         f"администратором")
        await message.reply("Доступ запрещён. Эта команда только для администраторов.")