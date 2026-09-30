"""Таблица слушателей потока — ячейка посещения мероприятия «МТС Линк» (часть 9).

Разведка (только чтение, через код существующего `AdminProgramsPage`, который уже
реализует и использует эту же вкладку/таблицу — `open_listeners_tab`/`listener_row`,
см. `ui/pages/admin_programs_page.py`) подтвердила вкладку «Слушатели» и структуру
строки (`<a href="/admin/users/{id}">`). Для обычных очных мероприятий ячейка посещения —
галка (checkbox), которую ставят/снимают вручную; часть 9 заменяет её для мероприятий
«МТС Линк» на процент по фактической длительности вебинара (>=75% — галка, иначе число).
Сам селектор ячейки посещения по конкретному мероприятию в таблице не подтверждён — новый
функционал, разведки в браузере в этой среде нет.
TODO: уточнить после появления ветки — селектор ячейки посещения и её состояний.
"""
from playwright.sync_api import Page, Locator, expect
from ui.pages.admin_programs_page import AdminProgramsPage
from config.settings import settings


class StreamListenersPage(AdminProgramsPage):
    """Расширяет вкладку «Слушатели потока» ячейкой посещения мероприятий «МТС Линк» —
    наследуется от AdminProgramsPage, чтобы переиспользовать open_listeners_tab/
    listener_row без дублирования (та же вкладка того же потока)."""

    def __init__(self, page: Page):
        super().__init__(page)

    def attendance_cell(self, user_id, schedule_item_id: int) -> Locator:
        """Ячейка посещения конкретного мероприятия в строке слушателя."""
        return self.listener_row(user_id).locator(
            f"[data-qa='attendance-cell-{schedule_item_id}']"
        )

    def attendance_cell_text(self, user_id, schedule_item_id: int) -> str:
        cell = self.attendance_cell(user_id, schedule_item_id)
        expect(cell).to_be_visible(timeout=settings.UI_TIMEOUT)
        return (cell.text_content() or "").strip()

    def is_attendance_checkmark(self, user_id, schedule_item_id: int) -> bool:
        """>=75% фактической длительности — галка вместо процента (часть 9)."""
        cell = self.attendance_cell(user_id, schedule_item_id)
        return cell.locator("i.mdi-check").is_visible(timeout=5000)

    def is_attendance_empty(self, user_id, schedule_item_id: int) -> bool:
        """Пусто, пока статистика по вебинару ещё не пришла из МТС Линк."""
        return self.attendance_cell_text(user_id, schedule_item_id) == ""
