from aiogram.types import Message, CallbackQuery, Update
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, WebApp
from aiogram_dialog.api.exceptions import UnknownIntent

from app.config import settings
from app.core.database import get_session
from app.handlers import BaseHandler
from app.handlers.admin.utils import AdminFilter
from app.handlers.dao import UserDAO, UserStatusDAO
from app.handlers.user.router_user import MainDialogStates
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AdminDialogStates(StatesGroup):
    main = State()
    admin_menu = State()


def get_user_from_update(event: Update):
    if isinstance(event, Update):
        if event.callback_query:
            return event.callback_query.from_user
        elif event.message:
            return event.message.from_user
    elif isinstance(event, CallbackQuery):
        return event.from_user
    elif isinstance(event, Message):
        return event.from_user
    return None


async def on_admin_panel_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = dialog_manager.event.from_user.id
    logger_my.debug(f"Администратор {user_id} нажал 'Панель администратора'")
    await dialog_manager.switch_to(AdminDialogStates.admin_menu)


async def on_back_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.debug(f"Администратор {user_id} вернулся в главное меню")
    await dialog_manager.switch_to(AdminDialogStates.main)


async def on_exit_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.debug(f"Администратор {user_id} вышел из админ-меню")
    await callback.message.answer("Админ-меню закрыто. Теперь вам доступна команда /start и другие.")
    await dialog_manager.done()


async def is_admin_root(data, widget, manager: DialogManager) -> bool:
    telegram_id = manager.event.from_user.id
    admin_root_ids = settings.admin_root
    return str(telegram_id) in admin_root_ids.split(",")


def is_admin_root_sync(data, widget, manager: DialogManager) -> bool:
    telegram_id = manager.event.from_user.id
    admin_root_ids = settings.admin_root
    return str(telegram_id) in admin_root_ids.split(",")


async def on_grant_access_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.debug(f"Супер-администратор {user_id} запросил выдачу прав администратора для себя")

    async with get_session() as session:
        user_dao = UserDAO(session)
        user = await user_dao.find_by_telegram_id(user_id)
        if not user:
            logger_my.error(f"Пользователь с telegram_id={user_id} не найден")
            await callback.message.answer("Пользователь не найден в базе данных.")
            return

        status_dao = UserStatusDAO(session)
        admin_status = await status_dao.find_one_or_none(filters={"status": "админ"})
        if not admin_status:
            logger_my.error("Статус 'админ' не найден в базе данных")
            await callback.message.answer("Статус 'админ' не найден в базе данных.")
            return

        if user.status_id == admin_status.id:
            logger_my.debug(f"Пользователь {user_id} уже имеет статус 'админ'")
            await callback.message.answer("Вы уже являетесь администратором.")
            return

        user.status_id = admin_status.id
        await session.commit()
        logger_my.debug(f"Пользователю {user_id} установлен статус 'админ'")
        await callback.message.answer("Вам успешно выданы права администратора!")


def admin_dialog() -> Dialog:
    return Dialog(
        Window(
            Const("Добро пожаловать в админ-панель! Что хотите сделать?"),
            Button(
                text=Const("Панель администратора"),
                id="admin_panel",
                on_click=on_admin_panel_click
            ),
            state=AdminDialogStates.main,
        ),
        Window(
            Const("Выберите действие в админ-панели:"),
            WebApp(text=Const("Перейти в панель администратора:"), url=Const('https://lynxwheelsspec.ru/')),
            Button(
                text=Const("Выдать права доступа"),
                id="grant_access",
                on_click=on_grant_access_click,
                when=is_admin_root_sync
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


async def is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"

async def is_group_chat(message: Message) -> bool:
    return message.chat.type in ["group", "supergroup"]


async def on_group_chat_command(message: Message) -> None:
    logger.debug(
        f"Получена команда {message.text} в групповом чате {message.chat.id} от пользователя {message.from_user.id}")
    await message.answer(
        "Этот бот работает только в личных сообщениях. Пожалуйста, напишите мне в личный чат!"
    )


class AdminHandler(BaseHandler):
    def __init__(self, dp):
        self.dialog = admin_dialog()
        super().__init__(dp)
        self.dp.include_router(self.dialog)

    def register_handlers(self):
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]),
                        is_private_chat, AdminFilter())(self.admin_command)
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]), is_private_chat, ~AdminFilter())(
            self.on_non_admin_access)
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]),
                        is_group_chat, AdminFilter())(on_group_chat_command)

    async def set_logger_middleware(self, handler, event, data: dict):
        self.logger.debug("Используется обновлённая версия set_logger_middleware v2.3")
        try:
            data["logger"] = self.logger
            return await handler(event, data)
        except UnknownIntent as e:
            error_message = str(e)
            intent_id = error_message.split("intent id: ")[-1] if "intent id: " in error_message else "unknown"
            user = get_user_from_update(event)
            user_id = user.id if user else "unknown"

            # Логируем с явной обработкой Unicode
            self.logger.debug(
                f"Тип события: {type(event)}, содержимое: {event}".encode('utf-8', errors='replace').decode('utf-8'))
            self.logger.warning(
                f"Устаревший контекст для intent_id={intent_id}, пользователь={user_id}. Сбрасываем диалог."
            )

            message = None
            if isinstance(event, Update) and event.callback_query:
                self.logger.debug(f"Событие является Update с CallbackQuery, извлекаем сообщение")
                message = event.callback_query.message
            elif isinstance(event, CallbackQuery):
                self.logger.debug(f"Событие является CallbackQuery, извлекаем сообщение")
                message = event.message
            else:
                self.logger.debug(f"Событие не является CallbackQuery, редактирование сообщения невозможно")

            dialog_manager = data.get("dialog_manager")
            self.logger.debug(f"dialog_manager: {dialog_manager}")

            if message:
                self.logger.debug(f"Сообщение найдено: message_id={message.message_id}, chat_id={message.chat.id}")
                try:
                    await message.delete()
                    self.logger.debug(
                        f"Удалено сообщение для intent_id={intent_id}, пользователь={user_id}, message_id={message.message_id}"
                    )
                except Exception as delete_error:
                    self.logger.warning(f"Не удалось удалить сообщение: {str(delete_error)}")

            if dialog_manager:
                try:
                    await dialog_manager.reset_stack()
                    dialog_manager.dialog_data.clear()
                    if dialog_manager.current_context() and dialog_manager.current_context().state in [
                        AdminDialogStates.main,
                        AdminDialogStates.admin_menu
                    ]:
                        await dialog_manager.start(state=AdminDialogStates.main, mode=StartMode.RESET_STACK)
                        if message:
                            await message.answer("Диалог устарел. Возвращаемся в админ-панель!")
                    else:
                        await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)
                        if message:
                            await message.answer("Диалог устарел. Начинаем заново!")
                    if isinstance(event, Update) and event.callback_query:
                        await event.callback_query.answer()
                    elif isinstance(event, CallbackQuery):
                        await event.answer()
                except Exception as reset_error:
                    self.logger.error(f"Ошибка при сбросе диалога: {str(reset_error)}", exc_info=True)
                    if message:
                        await message.answer("Произошла ошибка. Пожалуйста, начните заново с команды /start.")
                    if isinstance(event, Update) and event.callback_query:
                        await event.callback_query.answer()
                    elif isinstance(event, CallbackQuery):
                        await event.answer()
            else:
                self.logger.warning("dialog_manager отсутствует, сброс диалога невозможен")
                if message:
                    await message.answer("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                if isinstance(event, Update) and event.callback_query:
                    await event.callback_query.answer()
                elif isinstance(event, CallbackQuery):
                    await event.answer()

            return None
        except Exception as e:
            self.logger.error(f"Ошибка в middleware: {str(e)}", exc_info=True)
            raise

    async def admin_command(self, message: Message, dialog_manager: DialogManager) -> None:
        user = message.from_user
        self.logger.debug(f"Администратор {user.id} ({user.first_name}) вызвал команду /admin")
        dialog_manager.middleware_data["logger"] = self.logger
        await dialog_manager.start(state=AdminDialogStates.main)

    async def on_non_admin_access(self, message: Message) -> None:
        self.logger.debug(f"Пользователь {message.from_user.id} попытался вызвать команду /admin, но не является "
                          f"администратором")
        await message.reply("Доступ запрещён. Эта команда только для администраторов.")
