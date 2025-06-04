import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Callable, Optional

from aiogram.types import InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from aiogram.enums import ContentType
from aiogram_dialog import Window, DialogManager, StartMode
from aiogram_dialog.api.entities import ChatEvent
from aiogram_dialog.widgets.kbd import Calendar, CalendarConfig, CalendarScope, CalendarUserConfig, SwitchTo, Back, \
    Button, Cancel
from aiogram_dialog.widgets.kbd.calendar_kbd import CalendarScopeView, CalendarMonthView, CalendarYearsView
from aiogram_dialog.widgets.text import Const, Format, Text
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.widget_event import WidgetEventProcessor
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import joinedload

from app.core.database import get_session, connection
from app.handlers.dao import SpecialEquipmentDAO, RequestStatusDAO, RequestDAO, CompanyContactDAO
from app.handlers.models import Request
from app.handlers.schemas import SpecialEquipmentIdFilterName, RequestStatusBase, RequestBase, RequestUpdate, \
    RequestFilter
from app.handlers.user.keyboards import paginated_requests_by_equipment, paginated_requests_by_date
from app.utils.logging import get_logger
from app.handlers.user.utils import check_equipment_availability, get_active_policy_url

logger = get_logger(__name__)

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


class CustomText(Text):
    def __init__(self, render_func: Callable[[Dict[str, Any], DialogManager], str]):
        super().__init__()
        self.render_func = render_func

    async def _render_text(self, data: Dict[str, Any], manager: DialogManager) -> str:
        return self.render_func(data, manager)


class EmptyView:
    async def render(self, config: CalendarConfig, offset: date, data: dict, manager: DialogManager) -> List[
        List[InlineKeyboardButton]]:
        return [[]]


def raw_from_date(d: date) -> int:
    diff = d - date(1970, 1, 1)
    return int(diff.total_seconds())


def empty_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=" ", callback_data="")


class MainDialogStates(StatesGroup):
    action_menu = State()
    select_category = State()
    select_equipment = State()
    view_equipment_details = State()
    confirm_select_equipment = State()
    select_date_buttons = State()
    select_date = State()
    confirm_date = State()
    enter_phone = State()
    confirm_phone = State()
    enter_address = State()
    confirm_address = State()
    create_request = State()
    request_sent = State()
    cancel_rent = State()
    cancel_by_date = State()
    cancel_by_equipment = State()
    view_request_details = State()
    confirm_delete_request = State()
    confirm_delete_all_requests = State()
    more_menu = State()
    contacts = State()


class CustomCalendarDaysView:
    def __init__(
            self,
            callback_generator: Callable[[str], str],
            available_dates_getter: Callable[[Dict[str, Any], DialogManager], Any],
            calendar_id: str,
    ):
        self.callback_generator = callback_generator
        self.available_dates_getter = available_dates_getter
        self.calendar_id = calendar_id  # Store the calendar ID
        self.date_text = Format("{date:%d}")
        self.today_text = Format("[{date:%d}]")
        self.weekday_text = CustomText(lambda data, manager: WEEKDAYS[(data["date"].weekday()) % 7])
        self.header_text = CustomText(lambda data, manager: f"🗓 {MONTHS[data['date'].month - 1]} {data['date'].year}")
        self.next_month_text = CustomText(
            lambda data, manager: f"{MONTHS[(data['date'].month - 1) % 12]} {data['date'].year} >>"
        )
        self.prev_month_text = CustomText(
            lambda data, manager: f"<< {MONTHS[(data['date'].month - 1) % 12]} {data['date'].year}"
        )

    async def _render_date_button(
            self,
            selected_date: date,
            today: date,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> InlineKeyboardButton:
        available_dates = await self.available_dates_getter(offset, manager)
        if selected_date < today or selected_date not in available_dates:
            logger.debug(f"Date {selected_date} is either past or not available, rendering empty button")
            return empty_button()

        current_data = {"date": selected_date, "data": data}
        text = self.today_text if selected_date == today else self.date_text
        raw_date = raw_from_date(selected_date)
        button_text = await text.render_text(current_data, manager)
        return InlineKeyboardButton(
            text=button_text,
            callback_data=self.callback_generator(str(raw_date)),
        )

    async def _render_days(self, config: CalendarConfig, offset: date, data: dict, manager: DialogManager) -> List[
        List[InlineKeyboardButton]]:
        # Используем отдельную переменную для смещения рендеринга
        offset_str = manager.dialog_data.get(f"{self.calendar_id}_offset")
        render_offset = datetime.fromisoformat(offset_str).date() if offset_str else offset

        available_dates = await self.available_dates_getter(render_offset, manager)
        keyboard = []
        today = datetime.now(config.timezone).date()
        start_of_month = render_offset.replace(day=1)
        days_in_month = (
                start_of_month.replace(month=start_of_month.month % 12 + 1) - timedelta(days=1)
        ).day if start_of_month.month < 12 else 31
        first_weekday = start_of_month.weekday()  # 0-6, корректировка не нужна

        # Добавляем пустые кнопки перед началом месяца
        week = [empty_button() for _ in range(first_weekday)]

        # Рендерим дни месяца
        for day in range(1, days_in_month + 1):
            current_date = start_of_month.replace(day=day)
            if current_date < config.min_date or current_date > config.max_date:
                week.append(empty_button())
            else:
                button = await self._render_date_button(current_date, today, render_offset, data, manager)
                week.append(button)

            if len(week) == 7:
                keyboard.append(week)
                week = []

        # Обрабатываем последнюю неделю
        if week:
            week += [empty_button() for _ in range(7 - len(week))]
            keyboard.append(week)

        return keyboard

    async def _render_week_header(
            self,
            config: CalendarConfig,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        header = [InlineKeyboardButton(text=day, callback_data="") for day in WEEKDAYS]
        return header

    async def _render_header(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        data = {"date": offset, "data": data}
        return [
            InlineKeyboardButton(
                text=await self.header_text.render_text(data, manager),
                callback_data="",
            )
        ]

    async def _render_pager(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        current_month = datetime.now().date().replace(day=1)
        curr_month = offset.month
        curr_year = offset.year
        next_month = (curr_month % 12) + 1
        next_year = curr_year + 1 if next_month == 1 else curr_year
        prev_month = (curr_month - 2) % 12 + 1
        prev_year = curr_year - 1 if prev_month == 12 else curr_year

        prev_end = offset.replace(day=1) - timedelta(days=1)
        prev_begin = prev_end.replace(day=1)
        next_begin = (
            offset.replace(day=1, month=next_month, year=next_year)
            if next_month != 1
            else offset.replace(day=1, month=1, year=next_year)
        )

        prev_month_data = {"month": prev_month, "date": prev_begin, "data": data}
        next_month_data = {"month": next_month, "date": next_begin, "data": data}

        prev_button = empty_button() if prev_begin < current_month or prev_begin < config.min_date else InlineKeyboardButton(
            text=await self.prev_month_text.render_text(prev_month_data, manager),
            callback_data=self.callback_generator(f"month:{prev_begin.isoformat()}"),
        )
        next_button = empty_button() if next_begin > config.max_date else InlineKeyboardButton(
            text=await self.next_month_text.render_text(next_month_data, manager),
            callback_data=self.callback_generator(f"month:{next_begin.isoformat()}"),
        )
        return [prev_button, next_button]

    async def render(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        # Получаем offset из dialog_data, если он там есть
        offset_str = manager.dialog_data.get(f"{self.calendar_id}_offset")
        render_offset = datetime.fromisoformat(offset_str).date() if offset_str else offset

        return [
            await self._render_header(config, render_offset, data, manager),
            await self._render_week_header(config, data, manager),
            *await self._render_days(config, render_offset, data, manager),
            await self._render_pager(config, render_offset, data, manager),
        ]


async def _get_available_dates(offset: date, manager: DialogManager) -> List[date]:
    start_of_month = offset.replace(day=1)
    next_month = (start_of_month.month % 12) + 1
    next_year = start_of_month.year + 1 if next_month == 1 else start_of_month.year
    end_of_month = start_of_month.replace(month=next_month, year=next_year) - timedelta(days=1)
    equipment_name = manager.dialog_data.get("equipment_name", "Неизвестно")
    cache_key = f"availability_{equipment_name}_{start_of_month.isoformat()}"

    # Проверяем, есть ли данные в кэше
    if cache_key in manager.dialog_data:
        cached_dates = manager.dialog_data[cache_key]
        available_dates = [datetime.fromisoformat(d).date() for d in cached_dates]
        logger.debug(f"Используются кэшированные даты для {cache_key}")
    else:
        # Если данных нет, запрашиваем их из базы
        async with get_session() as session:
            availability = await check_equipment_availability(
                equipment_name,
                session,
                start_date=datetime.combine(start_of_month, datetime.min.time()),
                end_date=datetime.combine(end_of_month, datetime.min.time()),
            )
            available_dates = [datetime.fromisoformat(d).date() for d in availability["available_dates"]]
            # Кэшируем даты
            manager.dialog_data[cache_key] = [d.isoformat() for d in available_dates]
            logger.debug(f"Закэшированы даты для {cache_key}")

    # Фильтруем даты, чтобы они попадали в текущий месяц
    filtered_dates = [d for d in available_dates if start_of_month <= d <= end_of_month]
    return filtered_dates


class CustomRentalCalendar(Calendar):
    def __init__(
            self,
            id: str,
            switch_to_state: Optional[State] = None,
            on_click: Optional[WidgetEventProcessor] = None,
            config: Optional[CalendarConfig] = None,
            when: Optional[Callable[[Dict[str, Any], Any, DialogManager], bool]] = None,
    ):
        self.id = id  # Store the id to avoid AttributeError
        self.switch_to_state = switch_to_state
        super().__init__(id=id, on_click=on_click or self.on_date_selected, config=config, when=when)

    async def on_date_selected(
            self,
            event: ChatEvent,
            widget: Any,
            manager: DialogManager,
            selected_date: date,
    ) -> None:
        manager.dialog_data["selected_date"] = selected_date.isoformat()
        if self.switch_to_state:
            await manager.switch_to(self.switch_to_state)

    async def _process_item_callback(self, c: CallbackQuery, data: str, dialog, manager: DialogManager) -> bool:
        if data.startswith("month:"):
            selected_date = date.fromisoformat(data[6:])
            new_offset = selected_date.replace(day=1)
            manager.dialog_data[f"{self.id}_offset"] = new_offset.isoformat()
            manager.dialog_data["offset"] = new_offset.isoformat()

            equipment_name = manager.dialog_data.get("equipment_name", "Неизвестно")
            old_offset_str = manager.dialog_data.get("offset", datetime.now().date().isoformat())
            old_offset = datetime.fromisoformat(old_offset_str).date()
            old_cache_key = f"availability_{equipment_name}_{old_offset.replace(day=1).isoformat()}"
            if old_cache_key in manager.dialog_data:
                del manager.dialog_data[old_cache_key]
                logger.debug(f"Очищен кэш для {old_cache_key}")

            start_of_month = new_offset
            next_month = (start_of_month.month % 12) + 1
            next_year = start_of_month.year + 1 if next_month == 1 else start_of_month.year
            end_of_month = start_of_month.replace(month=next_month, year=next_year) - timedelta(days=1)
            cache_key = f"availability_{equipment_name}_{start_of_month.isoformat()}"
            async with get_session() as session:
                availability = await check_equipment_availability(
                    equipment_name,
                    session,
                    start_date=datetime.combine(start_of_month, datetime.min.time()),
                    end_date=datetime.combine(end_of_month, datetime.min.time()),
                )
                new_dates = [datetime.fromisoformat(d).date() for d in availability["available_dates"]]
                manager.dialog_data[cache_key] = [d.isoformat() for d in new_dates]
                manager.dialog_data["available_dates"] = [d.isoformat() for d in new_dates]
                logger.debug(f"Предварительно загружены и закэшированы даты для {cache_key}: {new_dates}")

            await manager.show()
            return True
        return await super()._process_item_callback(c, data, dialog, manager)

    def _init_views(self) -> dict[CalendarScope, CalendarScopeView]:
        return {
            CalendarScope.DAYS: CustomCalendarDaysView(
                self._item_callback_data,
                available_dates_getter=lambda offset, manager: _get_available_dates(offset, manager),
                calendar_id=self.id,
            ),
            CalendarScope.MONTHS: CalendarMonthView(
                self._item_callback_data, self.config,
            ),
            CalendarScope.YEARS: CalendarYearsView(
                self._item_callback_data, self.config,
            ),
        }

    async def _get_user_config(self, data: dict, manager: DialogManager) -> CalendarUserConfig:
        today = datetime.now().date()
        max_date = date(today.year + 1, 12, 31)  # Конец следующего года
        min_date = date(today.year, 1, 1)  # Начало текущего года вместо today
        return CalendarUserConfig(
            firstweekday=0,
            min_date=min_date,
            max_date=max_date,
            timezone=datetime.now().astimezone().tzinfo,
        )


async def confirmation_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug("Calling confirmation_getter")

    equipment_name = dialog_manager.dialog_data.get("equipment_name", "Неизвестно")
    selected_date = dialog_manager.dialog_data.get("selected_date", "Не выбрана")

    if selected_date != "Не выбрана":
        try:
            date_obj = datetime.fromisoformat(selected_date)
            selected_date = date_obj.strftime("%d.%m.%Y")
        except ValueError as e:
            logger_my.error(f"Ошибка форматирования даты {selected_date}: {str(e)}")
            selected_date = "Ошибка формата даты"

    if dialog_manager.current_context().state == MainDialogStates.confirm_select_equipment:
        async with get_session() as session:
            equipment_dao = SpecialEquipmentDAO(session)
            equipment = await equipment_dao.find_one_or_none(SpecialEquipmentIdFilterName(name=equipment_name))
            if not equipment:
                logger_my.error(f"Техника с именем {equipment_name} не найдена")
                return {
                    "equipment_name": equipment_name,
                    "rental_price": 0,
                    "selected_date": selected_date,
                    "image_path": "https://iimg.su/i/7vTQV5",
                }

            image_path = equipment.image_path if equipment.image_path else "https://iimg.su/i/7vTQV5"

            return {
                "equipment_name": equipment_name,
                "rental_price": float(equipment.rental_price_per_day) if equipment.rental_price_per_day else 0,
                "selected_date": selected_date,
                "image_path": image_path,
            }

    return {
        "equipment_name": equipment_name,
        "selected_date": selected_date,
        "phone_number": dialog_manager.dialog_data.get("phone_number", "Не указан"),
        "address": dialog_manager.dialog_data.get("address", "Не указан"),
        "image_path": "https://iimg.su/i/7vTQV5",
    }


def create_confirmation_window(
        text: str,
        intermediate_state: State,
        next_state: State,
        fields: Optional[List[str]] = None,
        formats: Optional[List[str]] = None,
        use_equipment_image: bool = False,
) -> Window:
    widgets = [
        StaticMedia(
            url=Format("{image_path}") if use_equipment_image else "https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO,
        ),
        Const(text),
    ]

    if fields and formats:
        if len(fields) != len(formats):
            raise ValueError("Number of fields and formats must match")
        for field, format_str in zip(fields, formats):
            widgets.append(Format(format_str, when=lambda data, widget, manager: field in data))

    widgets.extend([
        SwitchTo(text=Const("Да ✅"), id="confirm_yes", state=next_state),
        Back(text=Const("Отмена ❌"), id="confirm_cancel"),
    ])

    return Window(
        *widgets,
        state=intermediate_state,
        getter=confirmation_getter,
    )


async def on_today_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    today = datetime.now().date()
    dialog_manager.dialog_data["selected_date"] = today.isoformat()
    logger_my.debug(f"Выбрана дата: {today}")
    await dialog_manager.switch_to(MainDialogStates.confirm_date)
    await callback.answer()


async def on_tomorrow_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    tomorrow = datetime.now().date() + timedelta(days=1)
    dialog_manager.dialog_data["selected_date"] = tomorrow.isoformat()
    logger_my.debug(f"Выбрана дата: {tomorrow}")
    await dialog_manager.switch_to(MainDialogStates.confirm_date)
    await callback.answer()


async def on_day_after_tomorrow_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    day_after_tomorrow = datetime.now().date() + timedelta(days=2)
    dialog_manager.dialog_data["selected_date"] = day_after_tomorrow.isoformat()
    logger_my.debug(f"Выбрана дата: {day_after_tomorrow}")
    await dialog_manager.switch_to(MainDialogStates.confirm_date)
    await callback.answer()


async def on_select_date_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.debug("Переход к выбору даты через календарь")
    data = dialog_manager.dialog_data
    await dialog_manager.start(
        state=MainDialogStates.select_date,
        data=data,
        mode=StartMode.NEW_STACK
    )
    await callback.answer()


async def enter_phone_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    data = {
        "selected_date": dialog_manager.dialog_data.get("selected_date", "Не выбрана"),
        "equipment_name": dialog_manager.dialog_data.get("equipment_name", "Неизвестно"),
        "error_message": dialog_manager.dialog_data.get("error_message", None),
    }
    return data


async def availability_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    equipment_name = dialog_manager.dialog_data.get("equipment_name", "Неизвестно")

    # Retrieve the offset as a string from dialog_data
    offset_str = dialog_manager.dialog_data.get("offset")

    # Convert to date object or use current date as default
    if offset_str:
        try:
            current_offset = datetime.fromisoformat(offset_str).date()
        except ValueError:
            logger_my.error(f"Invalid date format for offset: {offset_str}")
            current_offset = datetime.now().date()
    else:
        current_offset = datetime.now().date()

    # Now current_offset is guaranteed to be a date object
    start_of_month = current_offset.replace(day=1)
    next_month = (start_of_month.month % 12) + 1
    next_year = start_of_month.year + 1 if next_month == 1 else start_of_month.year
    end_of_month = start_of_month.replace(month=next_month, year=next_year) - timedelta(days=1)

    start_of_month_dt = datetime.combine(start_of_month, datetime.min.time())
    end_of_month_dt = datetime.combine(end_of_month, datetime.min.time())

    async with get_session() as session:
        cache_key = f"availability_{equipment_name}_{start_of_month.isoformat()}"
        cached_dates = dialog_manager.dialog_data.get(cache_key, [])

        if cached_dates:
            logger_my.debug(f"Используются кэшированные даты для {cache_key}")
            available_dates = [
                datetime.fromisoformat(date).date() if isinstance(date, str) else date
                for date in cached_dates
            ]
        else:
            availability = await check_equipment_availability(
                equipment_name, session, start_date=start_of_month_dt, end_date=end_of_month_dt
            )
            available_dates = [datetime.fromisoformat(date).date() for date in availability["available_dates"]]
            dialog_manager.dialog_data[cache_key] = [date.isoformat() for date in available_dates]
            dialog_manager.dialog_data["available_dates"] = available_dates
            logger_my.debug(f"Cached available dates in dialog_data: {available_dates}")

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        is_today_available = today in available_dates
        is_tomorrow_available = tomorrow in available_dates
        is_day_after_tomorrow_available = day_after_tomorrow in available_dates

        logger_my.debug(
            f"Доступность: сегодня={is_today_available}, завтра={is_tomorrow_available}, послезавтра={is_day_after_tomorrow_available}"
        )

        return {
            "is_available": len(available_dates) > 0,
            "message": availability["message"] if "availability" in locals() else f"Техника {equipment_name} доступна",
            "equipment_name": equipment_name,
            "is_today_available": is_today_available,
            "is_tomorrow_available": is_tomorrow_available,
            "is_day_after_tomorrow_available": is_day_after_tomorrow_available,
            "today": today,
            "tomorrow": tomorrow,
            "day_after_tomorrow": day_after_tomorrow,
        }


def create_rental_calendar_window(state: State, calendar_state: State, confirm_state: State) -> Window:
    return Window(
        StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
        Format("{message}", when=lambda data, widget, manager: not data["is_available"]),
        Const("Когда вам нужна спецтехника?", when=lambda data, widget, manager: data["is_available"]),
        Button(
            text=Format("Сегодня ({today:%d.%m.%Y})"),
            id="select_today",
            on_click=on_today_click,
            when=lambda data, widget, manager: data["is_available"] and data["is_today_available"],
        ),
        Button(
            text=Format("Завтра ({tomorrow:%d.%m.%Y})"),
            id="select_tomorrow",
            on_click=on_tomorrow_click,
            when=lambda data, widget, manager: data["is_available"] and data["is_tomorrow_available"],
        ),
        Button(
            text=Format("Послезавтра ({day_after_tomorrow:%d.%m.%Y})"),
            id="select_day_after_tomorrow",
            on_click=on_day_after_tomorrow_click,
            when=lambda data, widget, manager: data["is_available"] and data["is_day_after_tomorrow_available"],
        ),
        SwitchTo(text=Const("Выбрать дату 📅"), id="select_date", state=calendar_state),
        Back(text=Const("Назад"), id="back"),
        state=state,
        getter=availability_getter,
    )


def create_calendar_view_window(state: State, confirm_state: State) -> Window:
    return Window(
        StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
        Format("{message}", when=lambda data, widget, manager: not data["is_available"]),
        Const("Выберите дату аренды:"),
        CustomRentalCalendar(
            id="rental_calendar",
            switch_to_state=confirm_state,
        ),
        SwitchTo(text=Const("Назад"), id="back", state=MainDialogStates.select_date_buttons),
        state=state,
        getter=availability_getter,
    )


async def enter_address_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    data = {
        "selected_date": dialog_manager.dialog_data.get("selected_date", "Не выбрана"),
        "equipment_name": dialog_manager.dialog_data.get("equipment_name", "Неизвестно"),
        "phone_number": dialog_manager.dialog_data.get("phone_number", "Не указан"),
        "error_message": dialog_manager.dialog_data.get("error_message", None),
    }
    return data


async def create_request_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    user = dialog_manager.event.from_user
    return {
        "equipment_name": dialog_manager.dialog_data.get("equipment_name", "Неизвестно"),
        "selected_date": dialog_manager.dialog_data.get("selected_date", "Не выбрана"),
        "phone_number": dialog_manager.dialog_data.get("phone_number", "Не указан"),
        "address": dialog_manager.dialog_data.get("address", "Не указан"),
        "first_name": user.first_name,
        "username": user.username if user.username else "Не указан",
    }


async def on_cancel_by_date_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.info(f"Пользователь {dialog_manager.event.from_user.id} выбрал отмену аренды по дате")
    await dialog_manager.start(
        state=MainDialogStates.cancel_by_date,
        mode=StartMode.NORMAL
    )
    await callback.answer()


async def on_cancel_by_equipment_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    logger_my.info(f"Пользователь {dialog_manager.event.from_user.id} выбрал отмену аренды по названию спецтехники")
    await dialog_manager.start(
        state=MainDialogStates.cancel_by_equipment,
        mode=StartMode.NORMAL
    )
    await callback.answer()


def create_cancel_rent_window(state: State) \
        -> Window:
    return Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Const("Выберите способ отмены аренды:"),
        Button(
            text=Const("По дате 📅"),
            id="cancel_by_date",
            on_click=on_cancel_by_date_click,
        ),
        Button(
            text=Const("По названию спецтехники 🚜"),
            id="cancel_by_equipment",
            on_click=on_cancel_by_equipment_click,
        ),
        SwitchTo(text=Const("Назад ❌"), id='back_menu', state=MainDialogStates.action_menu),
        state=state,
    )


async def cancel_by_date_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user = dialog_manager.event.from_user
    tg_id = user.id
    items_per_page = 5
    current_page = dialog_manager.dialog_data.get("cancel_date_page", 0)
    cache_key = f"cached_requests_date_{tg_id}"

    # Проверяем, нужно ли принудительно обновить данные
    force_refresh = dialog_manager.dialog_data.get("force_refresh", False)
    if force_refresh or cache_key not in dialog_manager.dialog_data:
        async with get_session() as session:
            status_dao = RequestStatusDAO(session)
            status = await status_dao.find_one_or_none(RequestStatusBase(name="Новая"))
            if not status:
                logger_my.error("Статус 'Новая' не найден в базе данных")
                return {"requests": [], "total_pages": 1}

            request_dao = RequestDAO(session)
            requests = await request_dao.find_all(
                filters={"tg_id": tg_id, "status_id": status.id},
                order_by=Request.selected_date.asc()
            )
            all_requests = [
                (request.selected_date.strftime("%d.%m.%Y"), str(request.id))
                for request in requests
            ]
            dialog_manager.dialog_data[cache_key] = all_requests
            logger_my.debug(f"Заявки для tg_id={tg_id} закэшированы: {all_requests}")

        # Сбрасываем флаг принудительного обновления
        if force_refresh:
            dialog_manager.dialog_data["force_refresh"] = False
            logger_my.debug("Флаг force_refresh сброшен")
    else:
        all_requests = dialog_manager.dialog_data[cache_key]
        logger_my.debug(f"Используются кэшированные заявки для tg_id={tg_id} (всего: {len(all_requests)})")

    total_requests = len(all_requests)
    total_pages = (total_requests + items_per_page - 1) // items_per_page
    dialog_manager.dialog_data["total_cancel_date_pages"] = total_pages

    return {
        "requests": all_requests,
        "total_pages": total_pages
    }


async def cancel_by_equipment_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user = dialog_manager.event.from_user
    tg_id = user.id
    items_per_page = 5
    current_page = dialog_manager.dialog_data.get("cancel_equipment_page", 0)
    cache_key = f"cached_requests_equipment_{tg_id}"

    # Check cache for requests
    if cache_key in dialog_manager.dialog_data:
        all_requests = dialog_manager.dialog_data[cache_key]
        logger_my.debug(f"Using cached requests for tg_id={tg_id} (total: {len(all_requests)})")
    else:
        async with get_session() as session:
            status_dao = RequestStatusDAO(session)
            status = await status_dao.find_one_or_none(RequestStatusBase(name="Новая"))
            if not status:
                logger_my.error("Status 'Новая' not found in database")
                return {"requests": [], "total_pages": 1}

            # Fetch user requests with status "Новая" using a dictionary for filters
            request_dao = RequestDAO(session)
            requests = await request_dao.find_all(
                filters={"tg_id": tg_id, "status_id": status.id},
                order_by=Request.equipment_name.asc()
            )
            all_requests = [
                (request.equipment_name, str(request.id))
                for request in requests
            ]
            dialog_manager.dialog_data[cache_key] = all_requests
            logger_my.debug(f"Requests for tg_id={tg_id} cached: {all_requests}")

    total_requests = len(all_requests)
    total_pages = (total_requests + items_per_page - 1) // items_per_page
    dialog_manager.dialog_data["total_cancel_equipment_pages"] = total_pages

    return {
        "requests": all_requests,
        "total_pages": total_pages
    }


@connection()
async def on_cancel_all_requests_click(callback: CallbackQuery, button, dialog_manager: DialogManager, session) -> None:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    user = dialog_manager.event.from_user
    tg_id = user.id

    # Получаем статусы "Новая" и "Отменена"
    status_dao = RequestStatusDAO(session)
    status_new = await status_dao.find_one_or_none(RequestStatusBase(name="Новая"))
    status_cancelled = await status_dao.find_one_or_none(RequestStatusBase(name="Отменена"))
    if not status_new or not status_cancelled:
        logger_my.error("Статусы 'Новая' или 'Отменена' не найдены в базе данных")
        await callback.message.answer("Ошибка: необходимые статусы не найдены.")
        await callback.answer()
        return

    # Обновляем все заявки пользователя со статусом "Новая" на "Отменена"
    request_dao = RequestDAO(session)
    updated = await request_dao.update(
        filters={"tg_id": tg_id, "status_id": status_new.id},
        values=RequestUpdate(status_id=status_cancelled.id)
    )

    if updated > 0:
        logger_my.info(f"Все заявки пользователя {tg_id} отменены (всего: {updated})")
        await callback.message.answer(f"Все ваши заявки ({updated}) успешно отменены! ✅")
    else:
        logger_my.info(f"У пользователя {tg_id} нет активных заявок для отмены")
        await callback.message.answer("У вас нет активных заявок для отмены.")

    # Очищаем кэш
    cache_key_date = f"cached_requests_date_{tg_id}"
    cache_key_equipment = f"cached_requests_equipment_{tg_id}"
    if cache_key_date in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_date]
    if cache_key_equipment in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_equipment]

    await dialog_manager.switch_to(MainDialogStates.cancel_rent)
    await callback.answer()


async def request_details_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    request_id = dialog_manager.dialog_data.get("selected_request_id")
    async with get_session() as session:
        request_dao = RequestDAO(session)
        # Fetch the Request object with its status relationship eagerly loaded
        request = await session.get(
            Request,
            request_id,
            options=[joinedload(Request.status)]
        )
        if not request:
            return {"error": "Заявка не найдена"}
        return {
            "equipment_name": request.equipment_name,
            "selected_date": request.selected_date.strftime("%d.%m.%Y"),
            "phone_number": request.phone_number,
            "address": request.address,
            "first_name": request.first_name,
            "username": request.username or "Не указан",
            "status": request.status.name,  # Now safe to access without lazy loading
        }


async def on_delete_request_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    await dialog_manager.switch_to(MainDialogStates.confirm_delete_request)


async def on_confirm_delete_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    request_id = dialog_manager.dialog_data.get("selected_request_id")
    async with get_session() as session:
        request_dao = RequestDAO(session)
        updated = await request_dao.update(
            filters=RequestFilter(id=request_id),
            values=RequestUpdate(status_id=8)
        )
        await session.commit()  # Явная фиксация транзакции
        if updated > 0:
            await callback.message.answer("Заявка успешно удалена! ✅")
        else:
            await callback.message.answer("Не удалось обновить статус заявки. Проверьте её наличие.")
    # Очистка кэша
    tg_id = dialog_manager.event.from_user.id
    cache_key_date = f"cached_requests_date_{tg_id}"
    cache_key_equipment = f"cached_requests_equipment_{tg_id}"
    if cache_key_date in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_date]
        logger.debug(f"Кэш {cache_key_date} удалён")
    if cache_key_equipment in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_equipment]
        logger.debug(f"Кэш {cache_key_equipment} удалён")
    dialog_manager.dialog_data["force_refresh"] = True
    await dialog_manager.switch_to(MainDialogStates.cancel_by_date)


async def on_cancel_delete_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    await dialog_manager.switch_to(MainDialogStates.view_request_details)


async def on_confirm_delete_all_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    user = dialog_manager.event.from_user
    tg_id = user.id
    async with get_session() as session:
        # Создаем DAO для работы со статусами и заявками
        status_dao = RequestStatusDAO(session)
        request_dao = RequestDAO(session)

        # Получаем статусы "Новая" и "Отменена"
        status_new = await status_dao.find_one_or_none(RequestStatusBase(name="Новая"))
        status_cancelled = await status_dao.find_one_or_none(RequestStatusBase(name="Отменена"))

        # Проверяем, что статусы найдены
        if not status_new or not status_cancelled:
            await callback.message.answer("Ошибка: необходимые статусы не найдены.")
            return

        # Обновляем статус заявок с "Новая" на "Отменена"
        updated = await request_dao.update(
            filters={"tg_id": tg_id, "status_id": status_new.id},
            values=RequestUpdate(status_id=status_cancelled.id)
        )
        await session.commit()  # Фиксируем изменения

        # Отправляем сообщение пользователю
        if updated > 0:
            await callback.message.answer(f"Все ваши заявки ({updated}) успешно отменены! ✅")
        else:
            await callback.message.answer("У вас нет активных заявок для отмены.")

    # Очистка кэша
    cache_key_date = f"cached_requests_date_{tg_id}"
    cache_key_equipment = f"cached_requests_equipment_{tg_id}"
    if cache_key_date in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_date]
    if cache_key_equipment in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[cache_key_equipment]

    # Переключаем состояние диалога
    await dialog_manager.switch_to(MainDialogStates.cancel_rent)


async def on_cancel_delete_all_click(callback: CallbackQuery, button, dialog_manager: DialogManager) -> None:
    await dialog_manager.switch_to(MainDialogStates.cancel_by_date)


async def on_request_date_click(callback: CallbackQuery, widget, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_request_id"] = int(item_id)
    await manager.switch_to(MainDialogStates.view_request_details)


async def on_request_equipment_click(callback: CallbackQuery, widget, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_request_id"] = int(item_id)
    await manager.switch_to(MainDialogStates.view_request_details)


request_details_window = Window(
    StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
    Format("Детали заявки:"),
    Format("Техника: {equipment_name}"),
    Format("Дата: {selected_date}"),
    Format("Телефон: {phone_number}"),
    Format("Адрес: {address}"),
    Format("Имя: {first_name}"),
    Format("Username: @{username}"),
    Format("Статус: {status}"),
    Button(Const("Удалить заявку 🗑️"), id="delete_request", on_click=on_delete_request_click),
    SwitchTo(text=Const("Выбрать способ отмены аренды"), state=MainDialogStates.cancel_rent, id='back_menu_cancel'),
    state=MainDialogStates.view_request_details,
    getter=request_details_getter
)

confirm_delete_window = Window(
    StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
    Const("Вы уверены, что хотите отменить эту заявку?"),
    Button(Const("Да, удалить"), id="confirm_delete", on_click=on_confirm_delete_click),
    Button(Const("Нет, отменить"), id="cancel_delete", on_click=on_cancel_delete_click),
    state=MainDialogStates.confirm_delete_request,
)

confirm_delete_all_window = Window(
    StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
    Const("Вы уверены, что хотите отменить все ваши заявки?"),
    Button(Const("Да, удалить все"), id="confirm_delete_all", on_click=on_confirm_delete_all_click),
    Button(Const("Нет, отменить"), id="cancel_delete_all", on_click=on_cancel_delete_all_click),
    state=MainDialogStates.confirm_delete_all_requests,
)


def create_cancel_by_date_window(state: State) -> Window:
    return Window(
        StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
        Const("Выберите заявку для отмены (по дате):"),
        paginated_requests_by_date(on_request_date_click),
        Const("Заявок нет", when=lambda data, widget, manager: not data.get("requests")),
        Button(Const("Отменить все заявки 🚫"), id="cancel_all_requests_date",
               on_click=lambda c, b, m: m.switch_to(MainDialogStates.confirm_delete_all_requests)),
        SwitchTo(text=Const("Назад ❌"), id="back_to_cancel_rent", state=MainDialogStates.cancel_rent),
        state=state,
        getter=cancel_by_date_getter
    )


def create_cancel_by_equipment_window(state: State) -> Window:
    return Window(
        StaticMedia(url="https://iimg.su/i/7vTQV5", type=ContentType.PHOTO),
        Const("Выберите заявку для отмены (по спецтехнике):"),
        paginated_requests_by_equipment(on_request_equipment_click),
        Const("Заявок нет", when=lambda data, widget, manager: not data.get("requests")),
        Button(Const("Отменить все заявки 🚫"), id="cancel_all_requests_equipment",
               on_click=lambda c, b, m: m.switch_to(MainDialogStates.confirm_delete_all_requests)),
        SwitchTo(text=Const("Назад ❌"), id="back_to_cancel_rent", state=MainDialogStates.cancel_rent),
        state=state,
        getter=cancel_by_equipment_getter
    )


def create_more_menu_window(state: State) -> Window:
    return Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Const("Дополнительная информация:"),
        SwitchTo(
            text=Const("Контакты 📞"),
            id="contacts",
            state=MainDialogStates.contacts
        ),
        SwitchTo(
            text=Const("Назад в меню 🔙"),
            id="back_to_menu",
            state=MainDialogStates.action_menu
        ),
        state=state
    )


async def contacts_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    logger_my = dialog_manager.middleware_data.get("logger") or logger
    async with get_session() as session:
        policy_url = await get_active_policy_url(session)
        contact_dao = CompanyContactDAO(session)
        contact = await contact_dao.get_active_contact()
        if not contact:
            logger_my.warning("Активная контактная информация не найдена, используются значения по умолчанию")
            return {
                "policy_url": policy_url,
                "company_name": "СпецТехАренда",
                "description": "Аренда строительной техники для любых задач!",
                "phone": "+7 (800) 123-45-67",
                "email": "support@specteharenda.ru",
                "telegram": "@SpecTehSupport",
                "address": "г. Москва, ул. Строителей, д. 10",
                "work_hours": "Пн-Пт: 9:00–18:00",
                "website": None,
                "social_media": None,
                "requisites": None,
                "image_url": "https://iimg.su/i/7vTQV5"
            }
        return {
            "policy_url": policy_url,
            "company_name": contact.company_name,
            "description": contact.description,
            "phone": contact.phone,
            "email": contact.email,
            "telegram": contact.telegram,
            "address": contact.address,
            "work_hours": contact.work_hours,
            "website": contact.website,
            "social_media": contact.social_media,
            "requisites": contact.requisites,
            "image_url": contact.image_url
        }


async def contacts_getter_wrapper(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    data = await contacts_getter(dialog_manager, **kwargs)
    dialog_manager.dialog_data["telegram"] = data.get("telegram")
    return data


def create_contacts_window(state: State) -> Window:
    async def on_write_support_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
        telegram = manager.dialog_data.get("telegram")
        if not telegram:
            await callback.answer("Telegram поддержки не указан.", show_alert=True)
            return

        telegram_handle = telegram if telegram.startswith('@') else f"@{telegram}"
        telegram_chat_url = f"https://t.me/{telegram_handle.lstrip('@')}"
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Написать в поддержку 💬", url=telegram_chat_url)]]
        )

        support_message_id = manager.dialog_data.get("support_message_id")
        if support_message_id:
            try:
                await callback.message.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=support_message_id
                )
                logger.debug(f"Удалено предыдущее сообщение с ID {support_message_id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить предыдущее сообщение: {e}")
            manager.dialog_data["support_message_id"] = None

        try:
            new_message = await callback.message.answer(
                "Свяжитесь с нашей поддержкой!",
                reply_markup=reply_markup
            )
            manager.dialog_data["support_message_id"] = new_message.message_id
            logger.debug(f"Новое сообщение отправлено с ID {new_message.message_id}")

            async def delete_later(bot, chat_id, message_id, manager: DialogManager):
                await asyncio.sleep(10)
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    logger.debug(f"Сообщение с ID {message_id} автоматически удалено через 10 секунд")
                    async with manager.bg() as m:
                        if m.dialog_data.get("support_message_id") == message_id:
                            m.dialog_data["support_message_id"] = None
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение через таймер: {e}")

            asyncio.create_task(
                delete_later(callback.message.bot, callback.message.chat.id, new_message.message_id, manager)
            )

        except Exception as e:
            logger.error(f"Не удалось отправить сообщение: {e}")
            manager.dialog_data["support_message_id"] = None

        await callback.answer()

    widgets = [
        StaticMedia(
            url=Format("{image_url}"),
            type=ContentType.PHOTO
        ),
        Format("{company_name}"),
        Format("{description}"),
        Format("📱 Телефон: {phone}", when="phone"),
        Format("📧 Email: {email}", when="email"),
        Format("✅ Telegram: {telegram}", when="telegram"),
        Format("🏢 Адрес: {address}", when="address"),
        Format("🕒 График работы: {work_hours}", when="work_hours"),
        Format("🌐 Сайт: {website}", when="website"),
        Format("📱 Социальные сети: {social_media}", when="social_media"),
        Format("📋 Реквизиты: {requisites}", when="requisites"),
        Format("📄 [Политика конфиденциальности]({policy_url})"),
        Button(
            Const("Написать в поддержку 💬"),
            id="write_support",
            on_click=on_write_support_click,
            when="telegram"
        ),
        SwitchTo(
            text=Const("Назад 🔙"),
            id="back_to_more",
            state=MainDialogStates.more_menu
        )
    ]

    return Window(
        *widgets,
        state=state,
        getter=contacts_getter_wrapper
    )
