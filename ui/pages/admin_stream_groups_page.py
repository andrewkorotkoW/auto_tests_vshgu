"""Админка → поток → «Группы»: создание группы вручную, добавление ПЗ в группу,
добавление слушателей в группу.

Перенос src/ui/locators/admin_stream_groups_locators.py коллеги
(репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminStreamGroupsPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_stream(self, ui_base_url: str, program_id, stream_id) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/admin/programs/{program_id}/streams/{stream_id}")
        expect(self.page).to_have_url(
            re.compile(rf".*/admin/programs/{program_id}/streams/{stream_id}.*"),
            timeout=30000,
        )

    def open_groups_tab(self) -> None:
        tab = self.page.locator("xpath=//a[contains(@href,'/streams/') and .//span[normalize-space()='Группы']]")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)

    def create_group_manually(self, name: str) -> None:
        create_button = self.page.get_by_role("button", name="Создать")
        expect(create_button).to_be_visible(timeout=15000)
        create_button.click(timeout=5000)

        manually_button = self.page.get_by_role("button", name="Вручную")
        expect(manually_button).to_be_visible(timeout=15000)
        manually_button.click(timeout=5000)

        name_input = self.page.locator("input[placeholder='Название группы']")
        expect(name_input).to_be_visible(timeout=15000)
        name_input.fill(name, timeout=5000)

        submit_button = self.page.locator("xpath=//button[.//span[normalize-space()='Создать']]").last
        expect(submit_button).to_be_enabled(timeout=15000)
        submit_button.click(timeout=5000)

        expect(self.group_button(name)).to_be_visible(timeout=30000)

    def group_button(self, group_name: str) -> Locator:
        return self.page.locator(f"xpath=//button[contains(@class,'cursor-pointer') and normalize-space()='{group_name}']")

    def open_group(self, group_name: str) -> str:
        """Открыть группу по имени и вернуть её id, извлечённый из URL."""
        expect(self.group_button(group_name)).to_be_visible(timeout=15000)
        self.group_button(group_name).click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/group/\d+/homework.*"), timeout=30000)
        match = re.search(r"/group/(\d+)/", self.page.url)
        return match.group(1) if match else ""

    def add_practical_task(self, pz_name: str) -> None:
        add_button = self.page.get_by_role("main").get_by_role("button", name="Добавить")
        expect(add_button).to_be_visible(timeout=15000)
        add_button.click(timeout=5000)

        row = self.page.locator(f"xpath=//tr[contains(@class,'vs-table__row') and .//*[normalize-space()='{pz_name}']]")
        expect(row).to_be_visible(timeout=30000)
        row.locator("xpath=.//div[contains(@class,'v-simple-checkbox')]").click(timeout=5000)

        submit_button = self.page.locator("xpath=//button[.//span[normalize-space()='Добавить']]").last
        expect(submit_button).to_be_enabled(timeout=15000)
        submit_button.click(timeout=5000)

        expect(self.group_practical_task_row(pz_name)).to_be_visible(timeout=30000)

    def group_practical_task_row(self, pz_name: str) -> Locator:
        return self.page.locator(
            f"xpath=//tr[contains(@class,'vs-table__row') and .//*[contains(normalize-space(),'{pz_name}')]]"
        ).first

    def open_listeners_tab(self) -> None:
        tab = self.page.locator("xpath=//a[contains(@href,'/listeners') and normalize-space()='Слушатели']")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/group/\d+/listeners.*"), timeout=30000)

    def add_listener(self, email: str) -> None:
        add_button = self.page.get_by_role("main").get_by_role("button", name="Добавить")
        expect(add_button).to_be_visible(timeout=15000)
        add_button.click(timeout=5000)

        row = self.listener_row_in_modal(email)
        expect(row).to_be_visible(timeout=30000)
        row.locator("xpath=.//div[contains(@class,'v-simple-checkbox')]").click(timeout=5000)

        submit_button = self.page.locator("xpath=//button[.//span[normalize-space()='Добавить']]").last
        expect(submit_button).to_be_enabled(timeout=15000)
        submit_button.click(timeout=5000)

        expect(self.group_listener_row(email)).to_be_visible(timeout=30000)

    def listener_row_in_modal(self, email: str) -> Locator:
        return self.page.locator(f"xpath=//tr[contains(@class,'vs-table__row') and .//*[normalize-space()='{email}']]").first

    def group_listener_row(self, email: str) -> Locator:
        return self.page.locator(f"xpath=//tr[contains(@class,'vs-table__row') and .//*[normalize-space()='{email}']]").first
