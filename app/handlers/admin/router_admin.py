from aiogram.types import Message, CallbackQuery, Update
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Url
from aiogram_dialog.api.exceptions import UnknownIntent
from app.handlers import BaseHandler
from app.handlers.admin.utils import AdminFilter
from app.handlers.user.router_user import MainDialogStates
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AdminDialogStates(StatesGroup):
    main = State()
    admin_menu = State()


# Функция для извлечения пользователя из объекта Update
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
    logger_my.info(f"Администратор {user_id} нажал 'Панель администратора'")
    await dialog_manager.switch_to(AdminDialogStates.admin_menu)


async def on_view_stats_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.info(f"Администратор {user_id} запросил статистику")
    await callback.message.answer("Статистика: 100 пользователей, 50 активных.")


async def on_manage_users_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.info(f"Администратор {user_id} запросил управление пользователями")
    await callback.message.answer("Управление пользователями: [в разработке].")


async def on_back_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.info(f"Администратор {user_id} вернулся в главное меню")
    await dialog_manager.switch_to(AdminDialogStates.main)


async def on_exit_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.info(f"Администратор {user_id} вышел из админ-меню")
    await callback.message.answer("Админ-меню закрыто. Теперь вам доступна команда /start и другие.")
    await dialog_manager.done()


def admin_dialog() -> Dialog:
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
    def __init__(self, dp):
        self.dialog = admin_dialog()
        super().__init__(dp)
        self.dp.include_router(self.dialog)  # Регистрируем диалог при инициализации

    def register_handlers(self):
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]), AdminFilter())(self.admin_command)
        self.dp.message(Command(commands=["admin", "админ", "Админ", "Admin"]), ~AdminFilter())(
            self.on_non_admin_access)

    async def set_logger_middleware(self, handler, event, data: dict):
        # Добавляем маркер, чтобы подтвердить, что используется обновлённая версия кода
        self.logger.info("Используется обновлённая версия set_logger_middleware v2.2")
        try:
            data["logger"] = self.logger
            return await handler(event, data)
        except UnknownIntent as e:
            # Извлекаем intent_id из сообщения об ошибке
            error_message = str(e)
            intent_id = error_message.split("intent id: ")[-1] if "intent id: " in error_message else "unknown"
            # Извлекаем пользователя из события
            user = get_user_from_update(event)
            user_id = user.id if user else "unknown"
            # Добавляем отладку для проверки типа события
            self.logger.debug(f"Тип события: {type(event)}, содержимое: {event}")
            # Обработка устаревшего контекста
            self.logger.warning(
                f"Устаревший контекст для intent_id={intent_id}, пользователь={user_id}. Сбрасываем диалог.")

            # Извлекаем сообщение для редактирования или удаления
            message = None
            if isinstance(event, Update) and event.callback_query:
                self.logger.debug(f"Событие является Update с CallbackQuery, извлекаем сообщение")
                message = event.callback_query.message
            elif isinstance(event, CallbackQuery):
                self.logger.debug(f"Событие является CallbackQuery, извлекаем сообщение")
                message = event.message
            else:
                self.logger.debug(f"Событие не является CallbackQuery, редактирование сообщения невозможно")

            # Проверяем наличие dialog_manager для сброса диалога
            dialog_manager = data.get("dialog_manager")
            self.logger.debug(f"dialog_manager: {dialog_manager}")

            # Удаляем сообщение, если оно доступно
            if message:
                self.logger.debug(f"Сообщение найдено: message_id={message.message_id}, chat_id={message.chat.id}")
                try:
                    await message.delete()
                    self.logger.debug(
                        f"Удалено сообщение для intent_id={intent_id}, пользователь={user_id}, message_id={message.message_id}")
                except Exception as delete_error:
                    self.logger.warning(f"Не удалось удалить сообщение: {str(delete_error)}")

            # Редактируем сообщение или уведомляем пользователя
            if message:
                try:
                    if dialog_manager:
                        # Если dialog_manager доступен, сбрасываем диалог
                        try:
                            await dialog_manager.reset_stack()
                            dialog_manager.dialog_data.clear()
                            await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)
                            await message.edit_text("Диалог устарел. Начинаем заново! 🚀")
                            if isinstance(event, Update) and event.callback_query:
                                await event.callback_query.answer()
                            elif isinstance(event, CallbackQuery):
                                await event.answer()
                        except Exception as reset_error:
                            self.logger.error(f"Ошибка при сбросе диалога: {str(reset_error)}", exc_info=True)
                            await message.edit_text("Произошла ошибка. Пожалуйста, начните заново с команды /start.")
                            if isinstance(event, Update) and event.callback_query:
                                await event.callback_query.answer()
                            elif isinstance(event, CallbackQuery):
                                await event.answer()
                    else:
                        # Если dialog_manager отсутствует, просто уведомляем пользователя
                        self.logger.warning("dialog_manager отсутствует, сброс диалога невозможен")
                        await message.edit_text("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                        if isinstance(event, Update) and event.callback_query:
                            await event.callback_query.answer()
                        elif isinstance(event, CallbackQuery):
                            await event.answer()
                except Exception as edit_error:
                    self.logger.warning(f"Не удалось отредактировать сообщение: {str(edit_error)}")
                    # Если редактирование не удалось, отправляем новое сообщение
                    try:
                        if dialog_manager:
                            await dialog_manager.reset_stack()
                            dialog_manager.dialog_data.clear()
                            await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)
                            await message.answer("Диалог устарел. Начинаем заново! 🚀")
                        else:
                            self.logger.warning("dialog_manager отсутствует, сброс диалога невозможен")
                            await message.answer("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                        if isinstance(event, Update) and event.callback_query:
                            await event.callback_query.answer()
                        elif isinstance(event, CallbackQuery):
                            await event.answer()
                    except Exception as answer_error:
                        self.logger.error(f"Не удалось отправить новое сообщение: {str(answer_error)}")
            else:
                # Если сообщение недоступно, отправляем новое сообщение
                self.logger.warning("Сообщение для редактирования недоступно, отправляем новое уведомление")
                try:
                    if isinstance(event, Update) and event.callback_query:
                        if dialog_manager:
                            await dialog_manager.reset_stack()
                            dialog_manager.dialog_data.clear()
                            await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)
                            await event.callback_query.message.answer("Диалог устарел. Начинаем заново! 🚀")
                        else:
                            self.logger.warning("dialog_manager отсутствует, сброс диалога невозможен")
                            await event.callback_query.message.answer(
                                "Диалог устарел. Пожалуйста, начните заново с команды /start.")
                        await event.callback_query.answer()
                    elif isinstance(event, CallbackQuery):
                        if dialog_manager:
                            await dialog_manager.reset_stack()
                            dialog_manager.dialog_data.clear()
                            await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)
                            await event.message.answer("Диалог устарел. Начинаем заново! 🚀")
                        else:
                            self.logger.warning("dialog_manager отсутствует, сброс диалога невозможен")
                            await event.message.answer("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                        await event.answer()
                    elif isinstance(event, Update) and event.message:
                        await event.message.answer("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                    elif isinstance(event, Message):
                        await event.answer("Диалог устарел. Пожалуйста, начните заново с команды /start.")
                except Exception as answer_error:
                    self.logger.error(f"Не удалось отправить новое сообщение: {str(answer_error)}")

            return None  # Прерываем обработку, так как контекст устарел
        except Exception as e:
            self.logger.error(f"Ошибка в middleware: {str(e)}", exc_info=True)
            raise

    async def admin_command(self, message: Message, dialog_manager: DialogManager) -> None:
        user = message.from_user
        self.logger.info(f"Администратор {user.id} ({user.first_name}) вызвал команду /admin")
        dialog_manager.middleware_data["logger"] = self.logger
        await dialog_manager.start(state=AdminDialogStates.main)

    async def on_non_admin_access(self, message: Message) -> None:
        self.logger.info(f"Пользователь {message.from_user.id} попытался вызвать команду /admin, но не является "
                         f"администратором")
        await message.reply("Доступ запрещён. Эта команда только для администраторов.")
