from aiogram_dialog.widgets.common import ManagedScroll
from aiogram_dialog.widgets.kbd import ScrollingGroup, Select
from aiogram_dialog.widgets.text import Format
from operator import itemgetter
from app.utils.logging import get_logger
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager

logger = get_logger(__name__)

SCROLLING_HEIGHT = 5


def paginated_categories(on_click):
    async def update_category_page(event: CallbackQuery, scroll: "ManagedScroll", manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "category_ids:" in callback_data:
                page_str = callback_data.split("category_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get("total_category_pages", 1)
                logger.debug(f"Получено total_pages из dialog_data: {total_pages}")
                if 0 <= page < total_pages:
                    manager.dialog_data["category_page"] = page
                    logger.debug(f"Обновлена страница категорий: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы категорий: {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="s_scroll_categories",
            item_id_getter=itemgetter(1),
            items="categories",
            on_click=on_click,
        ),
        id="category_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_category_page,
    )


def paginated_equipment(on_click):
    logger.debug("Создание paginated_equipment")

    async def update_equipment_page(event: CallbackQuery, scroll: "ManagedScroll", manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "equipment_ids:" in callback_data:
                page_str = callback_data.split("equipment_ids:")[1]
                page = int(page_str)
                category_id = manager.start_data.get("category_id")
                if not category_id:
                    logger.error("category_id отсутствует в start_data")
                    return
                total_pages = manager.dialog_data.get(f"total_equipment_pages_{category_id}", 1)
                if 0 <= page < total_pages:
                    manager.dialog_data[f"equipment_page_{category_id}"] = page
                    logger.debug(f"Обновлена страница оборудования для category_id={category_id}: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы оборудования: {str(e)}")

    select_widget = Select(
        Format("{item[0]}"),
        id="s_scroll_equipment",
        item_id_getter=itemgetter(1),
        items="equipment",
        on_click=on_click,
    )
    scrolling_group = ScrollingGroup(
        select_widget,
        id="equipment_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_equipment_page,
    )
    logger.debug(f"Создана клавиатура с id=equipment_ids, содержит Select")
    return scrolling_group


def paginated_requests_by_date(on_click):
    async def update_request_date_page(event: CallbackQuery, scroll: "ManagedScroll", manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "request_date_ids:" in callback_data:
                page_str = callback_data.split("request_date_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get("total_cancel_date_pages", 1)
                logger.debug(f"Получено total_pages для заявок по дате: {total_pages}")
                if 0 <= page < total_pages:
                    manager.dialog_data["cancel_date_page"] = page
                    logger.debug(f"Обновлена страница заявок по дате: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы заявок по дате: {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="s_scroll_requests_date",
            item_id_getter=itemgetter(1),
            items="requests",
            on_click=on_click,
        ),
        id="request_date_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_request_date_page,
    )


def paginated_requests_by_equipment(on_click):
    async def update_request_equipment_page(event: CallbackQuery, scroll: "ManagedScroll",
                                            manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "request_equipment_ids:" in callback_data:
                page_str = callback_data.split("request_equipment_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get("total_cancel_equipment_pages", 1)
                logger.debug(f"Получено total_pages для заявок по спецтехнике: {total_pages}")
                if 0 <= page < total_pages:
                    manager.dialog_data["cancel_equipment_page"] = page
                    logger.debug(f"Обновлена страница заявок по спецтехнике: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы заявок по спецтехнике: {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="s_scroll_requests_equipment",
            item_id_getter=itemgetter(1),
            items="requests",
            on_click=on_click,
        ),
        id="request_equipment_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_request_equipment_page,
    )


def paginated_pending_payment_requests(on_click):
    async def update_pending_payment_page(event: CallbackQuery, scroll: "ManagedScroll",
                                          manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "pending_payment_ids:" in callback_data:
                page_str = callback_data.split("pending_payment_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get("total_pending_payment_pages", 1)
                logger.debug(f"Получено total_pages для заявок на оплату: {total_pages}")
                if 0 <= page < total_pages:
                    manager.dialog_data["pending_payment_page"] = page
                    logger.debug(f"Обновлена страница заявок на оплату: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы заявок на оплату: {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="s_scroll_pending_payment",
            item_id_getter=itemgetter(1),
            items="requests",
            on_click=on_click,
        ),
        id="pending_payment_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_pending_payment_page,
    )


def paginated_paid_invoices(on_click):
    async def update_paid_invoices_page(event: CallbackQuery, scroll: "ManagedScroll", manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if "paid_invoices_ids:" in callback_data:
                page_str = callback_data.split("paid_invoices_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get("total_paid_invoices_pages", 1)
                if 0 <= page < total_pages:
                    manager.dialog_data["paid_invoices_page"] = page
                    logger.debug(f"Обновлена страница оплаченных счетов: {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы оплаченных счетов: {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="s_scroll_paid_invoices",
            item_id_getter=itemgetter(1),
            items="transactions",
            on_click=on_click,
        ),
        id="paid_invoices_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_paid_invoices_page,
    )


def paginated_requests_in_progress(on_click):
    return paginated_requests_by_status("in_progress", on_click)


def paginated_requests_completed(on_click):
    return paginated_requests_by_status("completed", on_click)


def paginated_requests_by_status(status_key: str, on_click):
    async def update_page(event: CallbackQuery, scroll: "ManagedScroll", manager: DialogManager) -> None:
        try:
            callback_data = event.data
            if f"{status_key}_ids:" in callback_data:
                page_str = callback_data.split(f"{status_key}_ids:")[1]
                page = int(page_str)
                total_pages = manager.dialog_data.get(f"total_{status_key}_pages", 1)
                if 0 <= page < total_pages:
                    manager.dialog_data[f"{status_key}_page"] = page
                    logger.debug(f"Обновлена страница заявок '{status_key}': {page}")
                else:
                    logger.warning(f"Попытка установить недопустимую страницу: {page}, всего страниц: {total_pages}")
            else:
                logger.error(f"Неверный формат callback_data: {callback_data}")
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Ошибка при обновлении страницы заявок '{status_key}': {str(e)}")

    return ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id=f"s_scroll_{status_key}",
            item_id_getter=itemgetter(1),
            items="requests",
            on_click=on_click,
        ),
        id=f"{status_key}_ids",
        width=1,
        height=SCROLLING_HEIGHT,
        hide_on_single_page=True,
        hide_pager=False,
        on_page_changed=update_page,
    )
