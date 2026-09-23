"""Админка: дашборды статистики программ и курсов (/admin/learning-statistics/*).

Перенос локаторов src/ui/pages/dashboard_page.py коллеги (отдельная история
origin/feature/dashboard-autotests, код взят через `git show`, ветка не сливалась)
в наш Page Object.
"""
import re

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminDashboardPage(BasePage):
    PROGRAMS_PATH = "/admin/learning-statistics/programs"
    COURSES_PATH = "/admin/learning-statistics/courses"

    def __init__(self, page: Page):
        super().__init__(page)

    def open_programs_dashboard(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PROGRAMS_PATH}")
        expect(self.page).to_have_url(
            re.compile(r".*/admin/learning-statistics/programs.*"), timeout=30000
        )

    def open_courses_dashboard(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.COURSES_PATH}")
        expect(self.page).to_have_url(
            re.compile(r".*/admin/learning-statistics/courses.*"), timeout=30000
        )

    def search(self, name: str) -> None:
        search_input = self.page.locator("input[data-qa='km-search']").or_(
            self.page.locator("input[placeholder='Поиск']")
        )
        expect(search_input.first).to_be_visible(timeout=15000)
        search_input.first.fill(name, timeout=5000)
        search_input.first.press("Enter")

    def row(self, entity_name: str) -> Locator:
        safe = entity_name.replace("'", "")
        return self.page.locator(
            f"xpath=//tr[.//a[normalize-space()='{safe}'] or .//*[normalize-space()='{safe}']]"
        )

    def row_cell(self, row: Locator, cell_index: int) -> Locator:
        return row.locator(f"xpath=.//td[{cell_index}]")

    def find_row(self, entity_name: str) -> Locator:
        """Найти строку сущности по имени: поиск + ожидание появления строки в таблице."""
        self.search(entity_name)
        row = self.row(entity_name)
        expect(row).to_be_visible(timeout=30000)
        return row

    def assert_program_row(
        self,
        program_name: str,
        *,
        schedule_items_completeness: int = None,
        assignments_count: int = None,
        assignments_new: int = None,
        assignments_in_progress: int = None,
        assignments_passed: int = None,
    ) -> None:
        """Проверить значения ячеек строки программы. Столбцы совпадают с
        /admin/learning-statistics/programs: 6 — завершённость мероприятий,
        7 — всего назначений, 8 — новых, 9 — в процессе, 10 — пройдено."""
        row = self.find_row(program_name)
        checks = {
            6: schedule_items_completeness,
            7: assignments_count,
            8: assignments_new,
            9: assignments_in_progress,
            10: assignments_passed,
        }
        for cell_index, value in checks.items():
            if value is not None:
                expect(self.row_cell(row, cell_index)).to_contain_text(str(value), timeout=15000)

    def assert_course_row(
        self,
        course_name: str,
        *,
        passed_percentage: int = None,
        total: int = None,
        not_started: int = None,
        in_progress: int = None,
        passed: int = None,
    ) -> None:
        """Проверить значения ячеек строки курса. Столбцы совпадают с
        /admin/learning-statistics/courses: 5 — % пройденных, 6 — всего,
        7 — не начато, 8 — в процессе, 9 — пройдено."""
        row = self.find_row(course_name)
        checks = {
            5: f"{passed_percentage}%" if passed_percentage is not None else None,
            6: total,
            7: not_started,
            8: in_progress,
            9: passed,
        }
        for cell_index, value in checks.items():
            if value is not None:
                expect(self.row_cell(row, cell_index)).to_contain_text(str(value), timeout=15000)
