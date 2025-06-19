from datetime import datetime
from decimal import Decimal
from aiogram import Router
from aiogram import F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Update, \
    KeyboardButton, ReplyKeyboardMarkup, PreCheckoutQuery
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, SwitchTo, Cancel, Back
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.api.exceptions import NoContextError, UnknownIntent
from pydantic import ValidationError

from app.config import settings
from app.handlers.models import PaymentTransaction
from app.handlers.user.window import create_confirmation_window, create_rental_calendar_window, enter_phone_getter, \
    create_request_getter, enter_address_getter, create_calendar_view_window, MainDialogStates, \
    create_cancel_rent_window, create_cancel_by_date_window, create_cancel_by_equipment_window, request_details_window, \
    confirm_delete_window, confirm_delete_all_window, create_more_menu_window, create_contacts_window, \
    create_pending_payment_window, create_payment_window, create_paid_invoices_window, \
    create_paid_invoice_details_window, create_my_requests_window, create_requests_in_progress_window, \
    create_requests_completed_window, create_request_details_window
from app.utils.logging import get_logger

from app.core.database import connection, async_session_maker
from app.handlers import BaseHandler
from app.handlers.schemas import TelegramIDModel, SpecialEquipmentIdFilter, \
    RequestCreate, EquipmentRentalHistoryCreate, SpecialEquipmentCategoryId, RequestStatusBase, RequestFilter, \
    RequestUpdate, UserCreate
from app.handlers.user.dao import AgreePolicyDAO
from app.handlers.dao import SpecialEquipmentCategoryDAO, SpecialEquipmentDAO, RequestDAO, EquipmentRentalHistoryDAO, \
    PaymentTransactionDAO, RequestStatusDAO, UserDAO, UserStatusDAO
from app.handlers.user.schemas import AgreePolicyModel
from app.handlers.user.utils import AgreePolicyFilter, get_active_policy_url, async_get_category_buttons, \
    async_get_equipment_buttons, async_get_equipment_details, validate_phone_number, no_err_filter
from app.handlers.user.keyboards import paginated_categories, paginated_equipment

logger = get_logger(__name__)

async def is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"

async def is_group_chat(message: Message) -> bool:
    return message.chat.type in ["group", "supergroup"]


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


async def on_start_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Начать'")
    await dialog_manager.switch_to(MainDialogStates.action_menu)


async def on_rent_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Аренда'")
    logger_my.debug(f"Переход в состояние {MainDialogStates.select_category}")
    try:
        await dialog_manager.switch_to(MainDialogStates.select_category)
    except NoContextError as e:
        logger_my.error(f"Ошибка контекста диалога при переходе в select_category: {str(e)}")
        await callback.message.answer("Ошибка: диалог не инициализирован. Попробуйте снова с /start.")
        await callback.answer()


@connection()
async def on_category_click(callback: CallbackQuery, widget, manager: DialogManager, item_id: str, session) -> None:
    logger_my = manager.middleware_data.get("logger") or logger
    category_id = int(item_id)
    manager.dialog_data["category_id"] = category_id
    logger_my.debug(f'category_id сохранился = {manager.dialog_data["category_id"]}')
    category_name = await get_category_name(category_id, session)
    logger_my.debug(f"Пользователь {manager.event.from_user.id} выбрал категорию '{category_name}' (id={category_id})")
    await manager.start(
        state=MainDialogStates.select_equipment,
        data={"category_id": category_id, "category_name": category_name},
        mode=StartMode.NORMAL
    )
    await callback.answer()


async def get_category_name(category_id, session):
    if not session:
        logger.error("Сессия базы данных отсутствует")
        return "Неизвестная категория"
    category_dao = SpecialEquipmentCategoryDAO(session)
    category = await category_dao.find_one_or_none(SpecialEquipmentCategoryId(id=category_id))
    return category.name if category else "Неизвестная категория"


@connection()
async def on_equipment_click(callback: CallbackQuery, widget, manager: DialogManager, item_id: str, session) -> None:
    logger_my = manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Обработчик on_equipment_click вызван для item_id={item_id}, callback_data={callback.data}")
    equipment_id = int(item_id)
    equipment_dao = SpecialEquipmentDAO(session)
    equipment = await equipment_dao.find_one_or_none(SpecialEquipmentIdFilter(id=equipment_id))
    if not equipment:
        logger_my.error(f"Техника с id={equipment_id} не найдена")
        await callback.message.answer("Техника не найдена.")
        await callback.answer()
        return
    category_id = equipment.category_id
    logger_my.debug(f"Пользователь {manager.event.from_user.id} выбрал технику '{equipment.name}' (id={equipment_id})")
    await manager.start(
        state=MainDialogStates.view_equipment_details,
        data={"equipment_id": equipment_id, 'category_id': category_id},
        mode=StartMode.NORMAL
    )
    await callback.answer()


async def on_back_to_menu_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    logger_my.debug(f"Пользователь {user_id} нажал 'Назад' в окне Категории, callback_data={callback.data}")
    try:
        current_state = dialog_manager.current_context().state if dialog_manager.current_context() else "None"
        logger_my.debug(f"Текущее состояние: {current_state}, переход в {MainDialogStates.action_menu}")
        await dialog_manager.switch_to(MainDialogStates.action_menu)
        logger_my.debug(f"Пользователь {user_id} успешно вернулся в главное меню")
    except Exception as e:
        logger_my.error(f"Ошибка при переходе в главное меню: {str(e)}", exc_info=True)
        await callback.message.answer("Ошибка при возврате в главное меню. Попробуйте снова.")
    await callback.answer()


async def on_pending_payment_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Заявки на оплату'")
    await dialog_manager.start(
        state=MainDialogStates.pending_payment_requests,
        mode=StartMode.NORMAL
    )
    await callback.answer()


async def on_more_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Подробнее'")
    await dialog_manager.switch_to(MainDialogStates.more_menu)
    await callback.answer()


async def on_exit_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user_id = callback.from_user.id
    try:
        logger_my.debug(f"Пользователь {user_id} вышел из меню")
        await callback.message.delete()
        dialog_manager.dialog_data.clear()
        await dialog_manager.reset_stack()
    except Exception as e:
        logger_my.error(f"Ошибка при выходе из меню для пользователя {user_id}: {str(e)}", exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте снова.")


async def go_menu(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(MainDialogStates.action_menu)


async def on_share_contact_click(callback, button, manager: DialogManager):
    contact_button = KeyboardButton(text="Отправить номер", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[contact_button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.answer(
        "Нажмите кнопку ниже, чтобы отправить ваш номер телефона.",
        reply_markup=keyboard
    )
    await callback.answer()


async def on_phone_number_input(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if message.contact:
        phone_number = message.contact.phone_number
        formatted_phone = validate_phone_number(phone_number)
        if formatted_phone:
            dialog_manager.dialog_data["phone_number"] = formatted_phone
            await dialog_manager.switch_to(MainDialogStates.confirm_phone)
        else:
            dialog_manager.dialog_data["error_message"] = "Неверный формат номера телефона."
    else:
        phone = message.text
        formatted_phone = validate_phone_number(phone)
        if formatted_phone:
            dialog_manager.dialog_data["phone_number"] = formatted_phone
            dialog_manager.dialog_data["error_message"] = ""
            await dialog_manager.switch_to(MainDialogStates.confirm_phone)
        else:
            dialog_manager.dialog_data["error_message"] = (
                "Неверный формат номера ❌\n"
                "Пожалуйста, введите номер в формате 89930057019 ✅\n"
                "Или нажмите Отправить номер"
            )


async def on_address_input(message: Message, widget: MessageInput, dialog_manager: DialogManager):
    if message.text:
        dialog_manager.dialog_data["address"] = message.text
        await dialog_manager.switch_to(MainDialogStates.confirm_address)
    else:
        dialog_manager.dialog_data["error_message"] = "Отправьте адрес текстом."


async def on_send_request_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user = callback.from_user
    data = dialog_manager.dialog_data
    bot = callback.message.bot

    # Извлекаем данные из диалога
    equipment_name = data.get("equipment_name")
    selected_date = data.get("selected_date")
    phone_number = data.get("phone_number")
    address = data.get("address")
    first_name = user.first_name
    username = user.username

    if not username:
        username = None

    async with async_session_maker() as session:
        try:
            equipment_dao = SpecialEquipmentDAO(session)
            equipment = await equipment_dao.find_by_name(equipment_name)
            if not equipment:
                raise ValueError(f"Спецтехника с именем '{equipment_name}' не найдено")

            request_dao = RequestDAO(session)
            new_request = RequestCreate(
                tg_id=user.id,
                equipment_name=equipment_name,
                selected_date=selected_date,
                phone_number=phone_number,
                address=address,
                first_name=first_name,
                username=username
            )
            temp = await request_dao.add(new_request)

            rental_history_dao = EquipmentRentalHistoryDAO(session)
            rental_history = EquipmentRentalHistoryCreate(
                equipment_id=equipment.id,
                start_date=selected_date,
                rental_price_at_time=equipment.rental_price_per_day
            )
            await rental_history_dao.add(rental_history)

            await session.commit()

            formatted_date = datetime.fromisoformat(selected_date).strftime("%d.%m.%Y")
            manager_message = (
                f"📢 Новая заявка\n"
                f"👤 Пользователь: {first_name} (@{username})\n"
                f"🚜 Техника: {equipment_name}\n"
                f"📅 Дата: {formatted_date}\n"
                f"📞 Телефон: {phone_number}\n"
                f"📍 Адрес: {address}\n"
                f"🆔 Telegram ID: {user.id}"
            )

            try:
                await bot.send_message(
                    chat_id=settings.chat_id,
                    text=manager_message
                )
                logger_my.debug(
                    f"Уведомление о новой заявке отправлено в чат менеджеров {settings.chat_id}")

            except Exception as e:
                logger_my.error(f"Ошибка при отправке уведомления в чат менеджеров: {str(e)}")

            await callback.message.answer("Заявка успешно отправлена!")
        except Exception as e:
            await session.rollback()
            return

    await dialog_manager.switch_to(MainDialogStates.request_sent)
    await callback.answer()


async def on_cancel_rent_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Отмена Аренды'")
    await dialog_manager.start(
        state=MainDialogStates.cancel_rent,
        mode=StartMode.RESET_STACK
    )
    await callback.answer()


async def on_paid_invoices_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Оплаченные счета'")
    await dialog_manager.start(
        state=MainDialogStates.paid_invoices,
        mode=StartMode.NORMAL
    )
    await callback.answer()


async def on_my_requests_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {dialog_manager.event.from_user.id} нажал 'Мои заявки'")
    await dialog_manager.start(
        state=MainDialogStates.my_requests,
        mode=StartMode.NORMAL
    )
    await callback.answer()


def main_dialog() -> Dialog:
    confirm_select_equipment_window = create_confirmation_window(
        text="Вы уверены, что хотите арендовать эту технику?",
        intermediate_state=MainDialogStates.confirm_select_equipment,
        next_state=MainDialogStates.select_date_buttons,
        fields=["equipment_name", "rental_price"],
        formats=[
            "Техника: {equipment_name}",
            "Цена аренды: {rental_price} руб/час",
        ],
        use_equipment_image=True
    )

    select_date_buttons_window = create_rental_calendar_window(
        state=MainDialogStates.select_date_buttons,
        calendar_state=MainDialogStates.select_date,
        confirm_state=MainDialogStates.confirm_date
    )

    confirm_date_window = create_confirmation_window(
        text="Подтвердите Дату аренды:",
        intermediate_state=MainDialogStates.confirm_date,
        next_state=MainDialogStates.enter_phone,
        fields=["equipment_name", "selected_date"],
        formats=["Техника: {equipment_name}", "Вы выбрали дату: {selected_date}"]
    )

    calendar_view_window = create_calendar_view_window(
        state=MainDialogStates.select_date,
        confirm_state=MainDialogStates.confirm_date
    )

    confirm_phone_window = create_confirmation_window(
        text="Подтвердите ваш номер телефона:",
        intermediate_state=MainDialogStates.confirm_phone,
        next_state=MainDialogStates.enter_address,
        fields=["phone_number"],
        formats=["Ваш номер телефона: {phone_number}"]
    )

    confirm_address_window = create_confirmation_window(
        text="Подтвердите адрес доставки:",
        intermediate_state=MainDialogStates.confirm_address,
        next_state=MainDialogStates.create_request,
        fields=["address"],
        formats=["Ваш адрес доставки: {address}"]
    )

    view_equipment_details_window = Window(
        StaticMedia(
            url=Format("{image_path}"),
            type=ContentType.PHOTO
        ),
        Format("Техника: {equipment_name}"),
        Format("Цена аренды: {rental_price} руб/час"),
        Format("Описание: {description}"),
        SwitchTo(text=Const(text='Арендовать'), id='rent_equipment', state=MainDialogStates.confirm_select_equipment),
        Cancel(text=Const(text='Назад'), id='back_1_menu'),
        Button(text=Const(text='Меню'), id='to_menu', on_click=go_menu),
        state=MainDialogStates.view_equipment_details,
        getter=async_get_equipment_details
    )

    enter_phone_window = Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Format("{error_message}", when="error_message"),
        Format("Техника: {equipment_name}", when=no_err_filter),
        Format("Дата: {selected_date}", when=no_err_filter),
        Format(
            "Введите номер телефона ниже\nили используйте кнопку 'Отправить номер'.",
            when=no_err_filter
        ),
        MessageInput(on_phone_number_input),
        Button(Const("Отправить номер"), id="share_contact", on_click=on_share_contact_click),
        Back(text=Const(text='Назад'), id='back'),
        state=MainDialogStates.enter_phone,
        getter=enter_phone_getter
    )

    enter_address_window = Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Format("{error_message}", when="error_message"),
        Format("Техника: {equipment_name}", when=no_err_filter),
        Format("Дата: {selected_date}", when=no_err_filter),
        Format("Номер телефона: {phone_number}", when=no_err_filter),
        Format(
            "Введите адрес доставки ниже.",
            when=no_err_filter
        ),
        MessageInput(on_address_input),
        Back(text=Const(text='Назад'), id='back'),
        state=MainDialogStates.enter_address,
        getter=enter_address_getter
    )

    create_request_window = Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Format("Заявка на аренду почти готова..."),
        Format("✅ Техника: {equipment_name}"),
        Format("✅ Дата: {selected_date}"),
        Format("✅ Номер телефона: {phone_number}"),
        Format("✅ Адрес доставки: {address}"),
        Format("✅ Имя: {first_name}"),
        Format("✅ tg: @{username}"),
        Button(Const('Отправить заявку менеджеру ✅'), id='send_request', on_click=on_send_request_click),
        Back(text=Const(text='Назад'), id='back'),
        Button(text=Const(text='Меню'), id='to_menu', on_click=go_menu),
        state=MainDialogStates.create_request,
        getter=create_request_getter
    )

    request_sent_window = Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Const("Заявка успешно отправлена менеджеру! ✅"),
        Button(text=Const(text='Меню'), id='to_menu', on_click=go_menu),
        state=MainDialogStates.request_sent,
    )

    cancel_rent_window = create_cancel_rent_window(
        state=MainDialogStates.cancel_rent
    )

    cancel_by_date_window = create_cancel_by_date_window(
        state=MainDialogStates.cancel_by_date
    )

    cancel_by_equipment_window = create_cancel_by_equipment_window(
        state=MainDialogStates.cancel_by_equipment
    )

    more_menu_window = create_more_menu_window(
        state=MainDialogStates.more_menu
    )

    contacts_window = create_contacts_window(
        state=MainDialogStates.contacts
    )
    pending_payment_window = create_pending_payment_window(
        state=MainDialogStates.pending_payment_requests
    )
    payment_window = create_payment_window(
        state=MainDialogStates.payment_details
    )

    paid_invoices_window = create_paid_invoices_window(MainDialogStates.paid_invoices)
    paid_invoice_details_window = create_paid_invoice_details_window(MainDialogStates.paid_invoice_details)
    my_requests_window = create_my_requests_window(MainDialogStates.my_requests)
    requests_in_progress_window = create_requests_in_progress_window(MainDialogStates.requests_in_progress)
    requests_completed_window = create_requests_completed_window(MainDialogStates.requests_completed)
    request_details_window_n = create_request_details_window(MainDialogStates.request_details)

    return Dialog(
        Window(
            Const("Главное меню"),
            StaticMedia(
                url="https://iimg.su/i/7vTQV5",
                type=ContentType.PHOTO
            ),
            Const("Выберите, что вы хотите сделать:"),
            Button(Const("Аренда"), id="rent", on_click=on_rent_click),
            Button(Const("Отмена Аренды"), id="cancel_rent", on_click=on_cancel_rent_click),
            Button(Const("Счета на оплату"), id="payment", on_click=on_pending_payment_click),
            Button(Const("Оплаченные счета"), id="paid_invoices", on_click=on_paid_invoices_click),
            Button(Const("Мои заявки"), id="my_requests", on_click=on_my_requests_click),
            Button(Const("Подробнее"), id="more", on_click=on_more_click),
            Button(Const("Выйти"), id="exit", on_click=on_exit_click),
            state=MainDialogStates.action_menu,
        ),
        Window(
            StaticMedia(
                url="https://iimg.su/i/7vTQV5",
                type=ContentType.PHOTO
            ),
            Const("Выберите категорию спецтехники:"),
            paginated_categories(on_category_click),
            Back(text=Const(text='Назад'), id='back_1_menu'),
            Button(text=Const(text='Меню'), id='to_menu', on_click=go_menu),
            state=MainDialogStates.select_category,
            getter=async_get_category_buttons
        ),
        Window(
            StaticMedia(
                url=Format("{path_image}"),
                type=ContentType.PHOTO
            ),
            Const("Выберите интересующую модель спецтехники:"),
            paginated_equipment(on_equipment_click),
            Const("Техника отсутствует", when=lambda data, widget, manager: not data.get("equipment")),
            Cancel(text=Const(text='Назад'), id='back_1_menu'),
            Button(text=Const(text='Меню'), id='to_menu', on_click=go_menu),
            state=MainDialogStates.select_equipment,
            getter=async_get_equipment_buttons
        ),
        view_equipment_details_window,
        confirm_select_equipment_window,
        select_date_buttons_window,
        confirm_date_window,
        enter_phone_window,
        confirm_phone_window,
        enter_address_window,
        confirm_address_window,
        create_request_window,
        request_sent_window,
        calendar_view_window,
        cancel_rent_window,
        cancel_by_date_window,
        cancel_by_equipment_window,
        request_details_window,
        confirm_delete_window,
        confirm_delete_all_window,
        more_menu_window,
        contacts_window,
        pending_payment_window,
        payment_window,
        paid_invoices_window,
        paid_invoice_details_window,
        my_requests_window,
        requests_in_progress_window,
        requests_completed_window,
        request_details_window_n,
    )


@connection()
async def on_agree_policy_click(callback: CallbackQuery, dialog_manager: DialogManager, session) -> None:
    user = callback.from_user
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug(f"Пользователь {user.id} ({user.first_name}) согласился с политикой конфиденциальности")
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

        user_dao = UserDAO(session)
        existing_user = await user_dao.find_by_telegram_id(user.id)
        if not existing_user:
            status_dao = UserStatusDAO(session)
            default_status = await status_dao.find_one_or_none({"status": "пользователь"})
            if not default_status:
                raise ValueError("Статус 'active' не найден в базе данных")

            await user_dao.add(UserCreate(
                telegram_id=user.id,
                username=user.username,
                status_id=default_status.id
            ))

        await callback.message.delete()

        await callback.message.answer("Спасибо, вы согласились с политикой конфиденциальности! "
                                      "Функционал разблокирован! Используйте /menu")
        await session.commit()
    except ValidationError as e:
        logger_my.error(f"Ошибка валидации данных для tg_id={user.id}: {str(e)}", exc_info=True)
        await callback.message.answer("Ошибка при сохранении данных. Попробуйте позже.")
        await session.rollback()
    except Exception as e:
        logger_my.error(f"Ошибка при добавлении данных для tg_id={user.id}: {str(e)}", exc_info=True)
        await callback.message.answer("Ошибка при сохранении данных. Попробуйте позже.")
        await session.rollback()
    await callback.answer()


async def on_group_chat_command(message: Message) -> None:
    logger.debug(
        f"Получена команда {message.text} в групповом чате {message.chat.id} от пользователя {message.from_user.id}")
    await message.answer(
        "Этот бот работает только в личных сообщениях. Пожалуйста, напишите мне в личный чат!"
    )


class UserHandler(BaseHandler):
    def __init__(self, dp: Router):
        self.dialog = main_dialog()
        super().__init__(dp)
        self.dp.include_router(self.dialog)

    def register_handlers(self):
        self.dp.message(Command(commands=["start", "menu", "меню", "начать", "main"]), is_private_chat,
                        AgreePolicyFilter())(self.start_command)
        self.dp.message(is_private_chat, ~AgreePolicyFilter())(self.on_no_policy_agreement)
        self.dp.callback_query(lambda c: c.data == "agree_policy")(on_agree_policy_click)

        self.dp.message(
            Command(commands=["start", "menu", "меню", "начать", "main"]),
            is_group_chat
        )(on_group_chat_command)

        self.dp.pre_checkout_query(lambda query: True)(handle_pre_checkout_query)
        self.dp.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)(handle_successful_payment)
        self.dp.callback_query(lambda c: c.data == "cancel_invoice")(cancel_invoice_handler)

    async def set_logger_middleware(self, handler, event, data: dict):
        try:
            data["logger"] = self.logger
            return await handler(event, data)
        except UnknownIntent as e:
            error_message = str(e)
            intent_id = error_message.split("intent id: ")[-1] if "intent id: " in error_message else "unknown"
            user = get_user_from_update(event)
            user_id = user.id if user else "unknown"
            self.logger.debug(f"Тип события: {type(event)}, содержимое: {event}")
            self.logger.warning(
                f"Устаревший контекст для intent_id={intent_id}, пользователь={user_id}. Сбрасываем диалог.")

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
                        f"Удалено сообщение для intent_id={intent_id}, пользователь={user_id}, message_id={message.message_id}")
                except Exception as delete_error:
                    self.logger.warning(f"Не удалось удалить сообщение: {str(delete_error)}")

            if message:
                try:
                    if dialog_manager:
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

            return None
        except Exception as e:
            self.logger.error(f"Ошибка в middleware: {str(e)}", exc_info=True)
            raise

    async def start_command(self, message: Message, dialog_manager: DialogManager) -> None:
        user = message.from_user
        self.logger.debug(f"Пользователь {user.id} ({user.first_name}) отправил команду /start или /menu")
        dialog_manager.middleware_data["logger"] = self.logger

        fsm_context = dialog_manager.middleware_data.get("fsm_context")
        if fsm_context:
            user_id_str = str(user.id)
            chat_id = message.chat.id
            storage_key = f"last_menu_message_id:{user_id_str}:{chat_id}"
            storage_data = await fsm_context.get_data()
            last_menu_message_id = storage_data.get(storage_key)
            if last_menu_message_id:
                try:
                    await message.bot.delete_message(chat_id=chat_id, message_id=last_menu_message_id)
                    self.logger.debug(f"Удалено старое сообщение с меню: message_id={last_menu_message_id}")
                except Exception as delete_error:
                    self.logger.warning(f"Не удалось удалить старое сообщение с меню: {str(delete_error)}")
                # Очищаем сохранённый message_id
                await fsm_context.set_data({storage_key: None})
        else:
            self.logger.warning("FSM-хранилище недоступно, не можем удалить старое сообщение с меню")

        await dialog_manager.start(state=MainDialogStates.action_menu, mode=StartMode.RESET_STACK)

    @connection()
    async def on_no_policy_agreement(self, message: Message, session) -> None:
        user = message.from_user
        self.logger.debug(
            f"Пользователь {user.id} ({user.first_name}) отправил сообщение без согласия с политикой")
        policy_url = await get_active_policy_url(session)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Согласен ✅", callback_data="agree_policy")],
            [InlineKeyboardButton(
                text="Политика конфиденциальности 📄",
                web_app=WebAppInfo(url=policy_url)
            )]
        ])
        await message.answer(
            text="Пожалуйста, ознакомьтесь и согласитесь с политикой конфиденциальности. "
                 "Тогда функционал бота станет доступен.",
            reply_markup=keyboard
        )


@connection()
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot, session) -> None:
    logger.debug(f"Получен предварительный запрос на оплату: {pre_checkout_query.id}")

    try:
        if pre_checkout_query.invoice_payload.startswith("request_"):
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=True
            )
            logger.debug(f"Успешно подтвержден предварительный запрос: {pre_checkout_query.id}")
        else:
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=False,
                error_message="Неверный идентификатор заказа."
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке предварительного запроса: {e}")
        await bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=False,
            error_message="Ошибка при подтверждении оплаты."
        )


@connection()
async def handle_successful_payment(message: Message, bot, session, **kwargs) -> None:
    successful_payment = message.successful_payment
    logger.debug(f"Получено уведомление об успешной оплате: {successful_payment.order_info}")

    payload = successful_payment.invoice_payload
    if not payload.startswith("request_"):
        logger.error(f"Неверный payload в успешной оплате: {payload}")
        return

    request_id = int(payload.replace("request_", ""))
    provider_payment_charge_id = successful_payment.provider_payment_charge_id
    telegram_id = message.from_user.id  # Получаем telegram_id из сообщения

    payment_dao = PaymentTransactionDAO(session)
    payment_transaction = PaymentTransaction(
        request_id=request_id,
        telegram_id=telegram_id,  # Добавляем telegram_id
        transaction_id=provider_payment_charge_id,
        amount=Decimal(str(successful_payment.total_amount / 100.0)),
        status="success",
        created_at=datetime.now()
    )
    await payment_dao.create(payment_transaction)

    request_dao = RequestDAO(session)
    status_dao = RequestStatusDAO(session)
    status_paid = await status_dao.find_one_or_none(RequestStatusBase(name="Оплачено"))
    if status_paid:
        await request_dao.update(
            filters=RequestFilter(id=request_id),
            values=RequestUpdate(status_id=status_paid.id)
        )
        await session.commit()
        logger.debug(f"Статус заявки {request_id} обновлен на 'Оплачено'")

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Оплата успешно завершена! Заявка #{request_id} оплачена. Номер транзакции: {provider_payment_charge_id}\n"
    )

    data = kwargs.get("data", {})
    dialog_manager = data.get("dialog_manager")
    if dialog_manager:
        await dialog_manager.show()


async def cancel_invoice_handler(callback_query: CallbackQuery):
    try:
        await callback_query.message.delete()
        logger.debug(f"Сообщение с инвойсом удалено пользователем {callback_query.from_user.id}")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    await callback_query.answer()
