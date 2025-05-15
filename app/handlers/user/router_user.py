from aiogram import Router
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const
from pydantic import ValidationError

from app.core.database import connection
from app.handlers import BaseHandler
from app.handlers.schemas import TelegramIDModel
from app.handlers.user.dao import AgreePolicyDAO
from app.handlers.user.schemas import AgreePolicyModel
from app.handlers.user.utils import AgreePolicyFilter, get_active_policy_url


class MainDialogStates(StatesGroup):
    main = State()
    action_menu = State()


async def on_start_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Начать'."""
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Начать'")
    await dialog_manager.switch_to(MainDialogStates.action_menu)


async def on_rent_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Аренда'."""
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Аренда'")
    await callback.message.answer("Вы выбрали 'Аренда'. Что дальше? 🚗")


async def on_cancel_rent_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Отмена Аренды'."""
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Отмена Аренды'")
    await callback.message.answer("Вы выбрали 'Отмена Аренды'. Укажите детали отмены. 🚫")


async def on_payment_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Счета на оплату'."""
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Счета на оплату'")
    await callback.message.answer("Вы выбрали 'Счета на оплату'. Вот ваши счета... 💸")


async def on_more_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Пополнение'."""
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Пополнение'")
    await callback.message.answer("Вы выбрали 'Пополнение'. Укажите сумму для пополнения. 💰")


async def on_exit_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    """Обработчик нажатия кнопки 'Выход'."""
    logger = dialog_manager.middleware_data.get("logger")
    user_id = callback.from_user.id
    if logger:
        logger.info(f"Пользователь {user_id} вышел из меню")
    await callback.message.answer("Меню закрыто.")
    await dialog_manager.done()  # Close the dialog to reset state


def main_dialog() -> Dialog:
    """Создает основной диалог с окнами."""
    return Dialog(
        Window(
            Const("Привет! 👋 Я твой чат-бот. Чем могу помочь?"),
            Button(
                Const("Начать"),
                id="start",
                on_click=on_start_click
            ),
            state=MainDialogStates.main,
        ),
        Window(
            Const("Главное меню"),
            StaticMedia(
                url="https://iimg.su/i/7vTQV5",  # Замените на реальный URL изображения
                type=ContentType.PHOTO
            ),
            Const("Выберите, что вы хотите сделать:"
                  ),
            Column(
                Button(Const("Аренда"), id="rent", on_click=on_rent_click),
                Button(Const("Отмена Аренды"), id="cancel_rent", on_click=on_cancel_rent_click),
                Button(Const("Счета на оплату"), id="payment", on_click=on_payment_click),
                Button(Const("Подробнее"), id="more", on_click=on_more_click),
                Button(Const("Выйти"), id="exit", on_click=on_exit_click)
            ),

            state=MainDialogStates.action_menu,
        )
    )


@connection()
async def on_agree_policy_click(callback: CallbackQuery, dialog_manager: DialogManager, session) -> None:
    """Обработчик нажатия кнопки 'Согласен'."""
    user = callback.from_user
    logger = dialog_manager.middleware_data.get("logger")
    if logger:
        logger.info(f"Пользователь {user.id} ({user.first_name}) согласился с политикой конфиденциальности")

    try:
        policy_dao = AgreePolicyDAO(session)
        existing_policy = await policy_dao.find_one_or_none(TelegramIDModel(telegram_id=user.id))
        if existing_policy:
            await callback.message.answer("Вы уже согласились с политикой конфиденциальности.")
            await callback.answer()
            return
        await policy_dao.add(AgreePolicyModel(
            telegram_id=user.id,
            name=user.first_name,
        ))
        await session.commit()
        await callback.message.answer("Спасибо, вы согласились с политикой конфиденциальности! "
                                      "Функционал разблокирован!")
    except ValidationError as e:
        if logger:
            logger.error(f"Ошибка валидации AgreePolicyModel для tg_id={user.id}: {str(e)}", exc_info=True)
        await callback.message.answer("Ошибка при сохранении согласия. Попробуйте позже.")
    except Exception as e:
        if logger:
            logger.error(f"Ошибка при добавлении согласия для tg_id={user.id}: {str(e)}", exc_info=True)
        await callback.message.answer("Ошибка при сохранении согласия. Попробуйте позже.")
    await callback.answer()


class UserHandler(BaseHandler):
    """Обработчик команд для пользователей."""

    def __init__(self, dp: Router):
        self.dialog = main_dialog()  # Инициализируем диалог до super().__init__
        super().__init__(dp)

    def register_handlers(self):
        """Регистрация обработчиков для пользователей."""
        # Регистрируем диалог
        self.dp.include_router(self.dialog)
        # Регистрируем команду для пользователей, согласных с политикой
        self.dp.message(Command(commands=["start", "menu", "меню", "начать", "main"]),
                        AgreePolicyFilter())(self.start_command)
        # Регистрируем обработчик для любых сообщений от пользователей, не согласных с политикой
        self.dp.message(~AgreePolicyFilter())(self.on_no_policy_agreement)
        # Регистрируем обработчик для кнопки "Согласен"
        self.dp.callback_query(lambda c: c.data == "agree_policy")(on_agree_policy_click)

    async def start_command(self, message: Message, dialog_manager: DialogManager) -> None:
        """Обработчик команды /start для пользователей, согласных с политикой."""
        user = message.from_user
        self.logger.info(f"Пользователь {user.id} ({user.first_name}) отправил команду /start")
        dialog_manager.middleware_data["logger"] = self.logger
        await dialog_manager.start(state=MainDialogStates.action_menu)

    @connection()
    async def on_no_policy_agreement(self, message: Message, session) -> None:
        """Обработчик для пользователей, не согласных с политикой конфиденциальности."""
        user = message.from_user
        self.logger.info(
            f"Пользователь {user.id} ({user.first_name}) отправил сообщение без согласия с политикой")
        # Получаем URL активной политики
        policy_url = await get_active_policy_url(session)
        # Создаем инлайн-клавиатуру с кнопками "Согласен" и WebApp
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Согласен ✅", callback_data="agree_policy")],
            [InlineKeyboardButton(
                text="Политика конфиденциальности 📄",
                web_app=WebAppInfo(url=policy_url)
            )]
        ])
        # Отправляем текст и кнопки
        await message.answer(
            text="Пожалуйста, ознакомьтесь и согласитесь с политикой конфиденциальности. "
                 "Тогда функционал бота станет доступен.",
            reply_markup=keyboard
        )
