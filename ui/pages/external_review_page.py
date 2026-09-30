"""Внешний проверяющий по персональной ссылке — без авторизации (04 §7,
docs/test_cases/p2p/05_external_reviewer.md). Функциональности ещё нет ни на одной ветке
(docs/missions/2026-09-30_tz2026_p2p.md), все селекторы ниже — предположение по аналогии
с формой критериев ui/pages/practical_task_page.py/reviewer_page.py.
# TODO: уточнить после ветки — каждый локатор.

В отличие от остальных page objects этого репозитория, страница открывается не через
авторизованную фикстуру admin_page/user_page из корневого conftest.py, а в отдельном
browser context без storage_state — см. tests/ui/practical_tasks/groups/test_group_practical_task_flow.py
(browser.new_context()/new_page()) для того же приёма на групповом ПЗ.
"""
from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class ExternalReviewPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_by_link(self, link: str) -> None:
        """Открыть персональную ссылку внешнего проверяющего — без логина/пароля
        (04 §7 п.4). Повторный переход по той же ссылке должен вернуть к списку работ
        (04 §7 п.8), а не требовать повторного входа."""
        self.page.goto(link)
        expect(self.works_list()).to_be_visible(timeout=30000)

    def works_list(self) -> Locator:
        # TODO: уточнить после ветки — список всех сданных работ ПЗ в потоке
        return self.page.locator("xpath=//div[contains(@class,'external-review-works-list')]")

    def work_row(self, author_full_name: str) -> Locator:
        # TODO: уточнить после ветки
        return self.works_list().locator(f"xpath=.//tr[.//*[normalize-space()='{author_full_name}']]")

    def open_work(self, author_full_name: str) -> None:
        row = self.work_row(author_full_name)
        expect(row).to_be_visible(timeout=30000)
        row.get_by_role("link", name="Проверить").click(timeout=5000)  # TODO: уточнить после ветки

    def expect_work_marked_reviewed(self, author_full_name: str) -> None:
        """Ранее проверенная работа помечена при повторном входе по ссылке
        (04 §7 п.8)."""
        # TODO: уточнить после ветки
        mark = self.work_row(author_full_name).locator("xpath=.//*[contains(@class,'reviewed-mark')]")
        expect(mark).to_be_visible(timeout=15000)

    # ── Форма критериев (та же структура, что у слушателя-проверяющего) ──

    def select_scale_criterion_value(self, criterion_label: str, value: str) -> None:
        # TODO: уточнить после ветки
        control = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{criterion_label}')]/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(control).to_be_visible(timeout=15000)
        control.click(timeout=5000)
        option = self.page.locator(f"xpath=//div[contains(@class,'v-menu__content')]//*[normalize-space()='{value}']").first
        expect(option).to_be_visible(timeout=10000)
        option.click(timeout=5000)

    def fill_text_criterion(self, criterion_label: str, text: str) -> None:
        # TODO: уточнить после ветки
        field = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{criterion_label}')]/following::textarea[1]"
        )
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def save_and_open_next_work(self) -> None:
        """Сохранить проверку и перейти к следующей работе из списка
        (04 §7 п.5)."""
        # TODO: уточнить после ветки
        button = self.page.get_by_role("button", name="Сохранить и перейти к следующей")
        expect(button).to_be_visible(timeout=15000)
        button.click(timeout=5000)
        expect(self.works_list()).to_be_visible(timeout=15000)

    # ── Ограничения роли «внешний» ────────────────────────────────────────

    def expect_no_dashboard_or_statistics(self) -> None:
        """У внешнего проверяющего нет личного кабинета/статистики/отчёта — только
        список работ и форма критериев (04 §3 — роли, 03 §2.5)."""
        # TODO: уточнить после ветки — проверка отсутствия характерных для ЛК элементов
        for absent_text in ("Личный кабинет", "Статистика", "Отчёт"):
            expect(self.page.get_by_text(absent_text, exact=False)).to_have_count(0)
