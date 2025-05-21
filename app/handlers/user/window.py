from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Callable, Optional

from aiogram.types import InlineKeyboardButton
from aiogram.enums import ContentType
from aiogram_dialog import Window, DialogManager
from aiogram_dialog.api.entities import ChatEvent
from aiogram_dialog.widgets.kbd import Calendar, CalendarConfig, CalendarScope, CalendarUserConfig, SwitchTo, Back
from aiogram_dialog.widgets.text import Const, Format, Text
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.widget_event import WidgetEventProcessor
from aiogram.fsm.state import State

from app.core.database import get_session
from app.utils.logging import get_logger
from app.handlers.user.utils import check_equipment_availability

logger = get_logger(__name__)

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


# Custom Text subclass to handle rendering with a provided function
class CustomText(Text):
    """
    A custom Text subclass that allows rendering with a provided function.
    """

    def __init__(self, render_func: Callable[[Dict[str, Any], DialogManager], str]):
        super().__init__()
        self.render_func = render_func

    async def _render_text(self, data: Dict[str, Any], manager: DialogManager) -> str:
        """
        Implement the abstract _render_text method using the provided render function.

        Args:
            data (Dict[str, Any]): Data for rendering.
            manager (DialogManager): Dialog manager instance.

        Returns:
            str: Rendered text.
        """
        return self.render_func(data, manager)


# Stub view for MONTHS and YEARS scopes to disable them
class EmptyView:
    """
    A stub view that returns an empty keyboard, used to disable MONTHS and YEARS views.
    """

    async def render(self, config: CalendarConfig, offset: date, data: dict, manager: DialogManager) -> List[
        List[InlineKeyboardButton]]:
        return [[]]


# Local definitions to avoid import issues
def raw_from_date(d: date) -> int:
    """
    Convert a date to a raw integer representing seconds since EPOCH (1970-01-01).

    Args:
        d (date): The date to convert.

    Returns:
        int: Seconds since EPOCH.
    """
    diff = d - date(1970, 1, 1)
    return int(diff.total_seconds())


def empty_button() -> InlineKeyboardButton:
    """
    Return an empty button for the calendar.

    Returns:
        InlineKeyboardButton: Empty button with space and no callback data.
    """
    return InlineKeyboardButton(text=" ", callback_data="")


async def confirmation_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Extracts data from dialog_data for the confirmation window.

    Args:
        dialog_manager (DialogManager): Dialog manager instance.
        **kwargs: Additional arguments.

    Returns:
        Dict[str, Any]: Dictionary with data from dialog_data.
    """
    data = dialog_manager.dialog_data.copy()
    logger.debug(f"Data in dialog_data for confirmation window: {data}")
    return data


def create_confirmation_window(
        text: str,
        intermediate_state: State,
        next_state: State,
        fields: Optional[List[str]] = None,
        formats: Optional[List[str]] = None
) -> Window:
    """
    Creates a confirmation window with specified text and two buttons: "Yes" and "Cancel".
    If fields and formats are provided, displays dialog_data in the specified formats.

    Args:
        text (str): Text to display in the window.
        intermediate_state (State): Intermediate state of the window.
        next_state (State): State to transition to upon clicking "Yes".
        fields (List[str], optional): List of fields from dialog_data to display.
        formats (List[str], optional): List of formats for displaying fields.

    Returns:
        Window: Window with text, data (if fields and formats are provided), and buttons.
    """
    widgets = [
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Const(text)
    ]

    if fields and formats:
        if len(fields) != len(formats):
            raise ValueError("Number of fields and formats must match")
        for field, format_str in zip(fields, formats):
            widgets.append(Format(format_str, when=lambda data, widget, manager: field in data))

    widgets.extend([
        SwitchTo(
            text=Const("Да ✅"),
            id="confirm_yes",
            state=next_state
        ),
        Back(
            text=Const("Отмена ❌"),
            id="confirm_cancel"
        )
    ])

    return Window(
        *widgets,
        state=intermediate_state,
        getter=confirmation_getter
    )


class CustomCalendarDaysView:
    """
    Custom calendar days view that displays only available dates for the current week, localized to Russian.
    """

    def __init__(
            self,
            callback_generator: Callable[[str], str],
            available_dates_getter: Callable[[Dict[str, Any], DialogManager], Any],
    ):
        self.callback_generator = callback_generator
        self.available_dates_getter = available_dates_getter
        self.date_text = Format("{date:%d}")
        self.today_text = Format("[{date:%d}]")
        # Локализация дней недели и заголовка с помощью CustomText
        self.weekday_text = CustomText(
            lambda data, manager: WEEKDAYS[(data["date"].weekday() + 1) % 7]
        )
        self.header_text = CustomText(
            lambda data, manager: f"🗓 {MONTHS[data['date'].month - 1]} {data['date'].year}"
        )
        self.zoom_out_text = Format("🔍")
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
            data: dict,
            manager: DialogManager,
    ) -> InlineKeyboardButton:
        available_dates = await self.available_dates_getter(data, manager)
        logger.debug(f"Selected date: {selected_date}, Available dates: {available_dates}")

        if selected_date not in available_dates:
            logger.debug(f"Date {selected_date} is not available, rendering empty button")
            return empty_button()

        current_data = {
            "date": selected_date,
            "data": data,
        }
        text = self.today_text if selected_date == today else self.date_text
        raw_date = raw_from_date(selected_date)
        button_text = await text.render_text(current_data, manager)
        logger.debug(f"Rendering button for date {selected_date}: {button_text}")
        return InlineKeyboardButton(
            text=button_text,
            callback_data=self.callback_generator(str(raw_date)),
        )

    async def _render_days(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        keyboard = []
        start_date = config.min_date  # Понедельник текущей недели
        today = datetime.now(config.timezone).date()
        logger.debug(
            f"Rendering days: start_date={start_date}, min_date={config.min_date}, max_date={config.max_date}, today={today}")

        row = []
        for row_offset in range(7):
            current_date = start_date + timedelta(days=row_offset)
            if current_date < today:  # Прошлые даты
                row.append(empty_button())
                logger.debug(f"Date {current_date} is in the past, added empty button")
            else:
                button = await self._render_date_button(
                    current_date, today, data, manager,
                )
                row.append(button)
        keyboard.append(row)
        return keyboard

    async def _render_week_header(
            self,
            config: CalendarConfig,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        header = [InlineKeyboardButton(text=day, callback_data="") for day in WEEKDAYS]
        logger.debug(f"Rendered week header: {[btn.text for btn in header]}")
        return header

    async def _render_header(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        """
        Render the header of the calendar, showing the current month and year, with no action on click.

        Args:
            config (CalendarConfig): Calendar configuration.
            offset (date): Current offset date.
            data (dict): Data from the window getter.
            manager (DialogManager): Dialog manager instance.

        Returns:
            List[InlineKeyboardButton]: List containing the header button.
        """
        data = {
            "date": offset,
            "data": data,
        }
        return [InlineKeyboardButton(
            text=await self.header_text.render_text(data, manager),
            callback_data="",  # No action on click
        )]

    async def _render_pager(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[InlineKeyboardButton]:
        curr_month = offset.month
        next_month = (curr_month % 12) + 1
        prev_month = (curr_month - 2) % 12 + 1
        prev_end = offset.replace(day=1) - timedelta(days=1)
        prev_begin = prev_end.replace(day=1)
        next_begin = (offset.replace(day=1, month=offset.month % 12 + 1)) if offset.month < 12 else offset.replace(
            day=1, month=1, year=offset.year + 1)
        if prev_end < config.min_date and next_begin > config.max_date:
            return []

        prev_month_data = {
            "month": prev_month,
            "date": prev_begin,
            "data": data,
        }
        curr_month_data = {
            "month": curr_month,
            "date": date(2018, curr_month, 1),
            "data": data,
        }
        next_month_data = {
            "month": next_month,
            "date": next_begin,
            "data": data,
        }
        prev_button = empty_button() if prev_end < config.min_date else InlineKeyboardButton(
            text=await self.prev_month_text.render_text(prev_month_data, manager),
            callback_data=self.callback_generator("-")
        )
        zoom_button = InlineKeyboardButton(
            text=await self.zoom_out_text.render_text(curr_month_data, manager),
            callback_data=self.callback_generator("M"),
        )
        next_button = empty_button() if next_begin > config.max_date else InlineKeyboardButton(
            text=await self.next_month_text.render_text(next_month_data, manager),
            callback_data=self.callback_generator("+")
        )
        return [prev_button, zoom_button, next_button]

    async def render(
            self,
            config: CalendarConfig,
            offset: date,
            data: dict,
            manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        return [
            await self._render_header(config, offset, data, manager),
            await self._render_week_header(config, data, manager),
            *await self._render_days(config, offset, data, manager),
            await self._render_pager(config, offset, data, manager),
        ]


class CustomRentalCalendar(Calendar):
    """
    Custom calendar for displaying available rental dates within the current week.
    """

    def __init__(
            self,
            id: str,
            switch_to_state: Optional[State] = None,
            on_click: Optional[WidgetEventProcessor] = None,
            config: Optional[CalendarConfig] = None,
            when: Optional[Callable[[Dict[str, Any], Any, DialogManager], bool]] = None
    ):
        self.switch_to_state = switch_to_state
        # Исправляем опечатку: 'son_click' -> 'on_click'
        super().__init__(id=id, on_click=on_click or self.on_date_selected, config=config, when=when)

    async def on_date_selected(
            self,
            event: ChatEvent,
            widget: Any,
            manager: DialogManager,
            selected_date: date
    ) -> None:
        """
        Handle date selection by storing the selected date and switching to the specified state.

        Args:
            event (ChatEvent): The event triggering the callback.
            widget: The calendar widget.
            manager (DialogManager): The dialog manager.
            selected_date (date): The selected date.
        """
        manager.dialog_data["selected_date"] = selected_date.isoformat()
        if self.switch_to_state:
            await manager.switch_to(self.switch_to_state)

    def _init_views(self) -> dict[CalendarScope, Any]:
        return {
            CalendarScope.DAYS: CustomCalendarDaysView(
                self._item_callback_data,
                available_dates_getter=self._get_available_dates,
            ),
            CalendarScope.MONTHS: EmptyView(),
            CalendarScope.YEARS: EmptyView(),
        }

    async def _get_user_config(self, data: dict, manager: DialogManager) -> CalendarUserConfig:
        today = datetime.now().date()
        days_since_monday = today.weekday()  # 0 для понедельника, 1 для вторника и т.д.
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return CalendarUserConfig(
            firstweekday=0,
            min_date=monday,
            max_date=sunday,
            timezone=datetime.now().astimezone().tzinfo
        )

    async def _get_available_dates(self, data: Dict[str, Any], manager: DialogManager) -> List[date]:
        """
        Retrieves the list of available rental dates from dialog_data.
        """
        available_dates = manager.dialog_data.get("available_dates", [])
        logger.debug(f"Retrieved available dates from dialog_data: {available_dates}")
        return available_dates


async def enter_phone_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    data = {
        "selected_date": dialog_manager.dialog_data.get("selected_date", "Не выбрана"),
        "equipment_name": dialog_manager.dialog_data.get("equipment_name", "Неизвестно"),
        "error_message": dialog_manager.dialog_data.get("error_message", None)
    }
    return data


async def availability_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    equipment_name = dialog_manager.dialog_data.get("equipment_name", "Неизвестно")
    async with get_session() as session:
        availability = await check_equipment_availability(equipment_name, session)
        available_dates = [datetime.fromisoformat(date).date() for date in availability["available_dates"]]
        dialog_manager.dialog_data["available_dates"] = available_dates
        logger.debug(f"Cached available dates in dialog_data: {available_dates}")
        return {
            "is_available": len(available_dates) > 0,
            "message": availability["message"],
            "equipment_name": equipment_name
        }


def create_rental_calendar_window(state: State, switch_to: State) -> Window:
    """
    Создает окно с календарем для выбора даты аренды или сообщение, если дат нет.

    Args:
        state (State): Состояние диалога для окна.
        switch_to (State): Состояние, на которое переключаемся после выбора даты.

    Returns:
        Window: Окно с календарем или сообщением в зависимости от доступности.
    """
    return Window(
        StaticMedia(
            url="https://iimg.su/i/7vTQV5",
            type=ContentType.PHOTO
        ),
        Format("{message}", when=lambda data, widget, manager: not data["is_available"]),
        Const("Выберите дату аренды:", when=lambda data, widget, manager: data["is_available"]),
        CustomRentalCalendar(
            id="rental_calendar",
            switch_to_state=switch_to,
            when=lambda data, widget, manager: data["is_available"]
        ),
        Back(text=Const("Назад"), id="back"),
        state=state,
        getter=availability_getter
    )


async def enter_address_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    data = {
        "selected_date": dialog_manager.dialog_data.get("selected_date", "Не выбрана"),
        "equipment_name": dialog_manager.dialog_data.get("equipment_name", "Неизвестно"),
        "phone_number": dialog_manager.dialog_data.get("phone_number", "Не указан"),
        "error_message": dialog_manager.dialog_data.get("error_message", None)
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
        "username": user.username if user.username else "Не указан"
    }
