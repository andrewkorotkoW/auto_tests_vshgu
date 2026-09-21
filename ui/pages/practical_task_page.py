"""Слушатель проходит ПЗ: программа → «Курсы и тесты» → карточка ПЗ →
скачивание документов, ответ текстом и файлом, редактирование общего ответа
(групповое ПЗ вторым участником).

Перенос src/ui/locators/user_programs_locators.py коллеги
(репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re
from pathlib import Path
from typing import Union

from playwright.sync_api import Page, Locator, Download, expect
from ui.pages.base_page import BasePage


class PracticalTaskPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_programs_list(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/programs")

    def program_title(self, program_name: str) -> Locator:
        return self.page.locator(f"xpath=//a[contains(@class,'description__title')][.//*[normalize-space()='{program_name}']]")

    def open_program(self, program_name: str) -> None:
        expect(self.program_title(program_name)).to_be_visible(timeout=30000)
        self.program_title(program_name).click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/program/.*"), timeout=30000)

    def open_courses_and_tests_tab(self) -> None:
        tab = self.page.locator("xpath=//span[normalize-space()='Курсы и тесты']")
        expect(tab).to_be_visible(timeout=15000)
        # force=True: вкладка Vuetify-таба, обычный клик иногда перехватывается соседней анимацией
        tab.click(timeout=5000, force=True)

    def practical_task_card(self, pz_name: str) -> Locator:
        return self.page.locator(f"xpath=//div[contains(@class,'activity-card__title') and contains(normalize-space(),'{pz_name}')]").first

    def open_practical_task(self, pz_name: str) -> None:
        card = self.practical_task_card(pz_name)
        expect(card).to_be_visible(timeout=30000)
        card.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*[?&]homework=\d+.*"), timeout=15000)

    @property
    def main_document_download_button(self) -> Locator:
        return self.page.locator(
            "xpath=//span[normalize-space()='Основной документ']"
            "/ancestor::div[contains(@class,'activity-details-layout')]//a[@download]"
        )

    @property
    def additional_materials_download_button(self) -> Locator:
        return self.page.locator(
            "xpath=//span[contains(normalize-space(),'Дополнительные материалы')]"
            "/ancestor::div[contains(@class,'activity-details-layout')]//a[@download]"
        )

    def download_main_document(self) -> Download:
        expect(self.main_document_download_button).to_be_visible(timeout=15000)
        with self.page.expect_download(timeout=15000) as download_info:
            self.main_document_download_button.click(timeout=5000)
        return download_info.value

    def download_additional_materials(self) -> Download:
        expect(self.additional_materials_download_button).to_be_visible(timeout=15000)
        with self.page.expect_download(timeout=15000) as download_info:
            self.additional_materials_download_button.click(timeout=5000)
        return download_info.value

    @property
    def answer_textarea(self) -> Locator:
        return self.page.locator("textarea.v-field__input").first

    def fill_answer(self, text: str) -> None:
        expect(self.answer_textarea).to_be_visible(timeout=15000)
        self.answer_textarea.fill(text, timeout=5000)

    def attach_answer_file(self, path: Union[str, Path]) -> None:
        attach_button = self.page.get_by_role("button", name="Прикрепить файл")
        expect(attach_button).to_be_visible(timeout=15000)
        with self.page.expect_file_chooser(timeout=15000) as file_chooser_info:
            attach_button.click(timeout=5000)
        file_chooser_info.value.set_files(str(path))

    def submit(self) -> None:
        submit_button = self.page.get_by_role("button", name="Отправить")
        expect(submit_button).to_be_visible(timeout=15000)
        submit_button.click(timeout=5000)

    def expect_sent_to_review(self) -> None:
        status = self.page.locator(
            "xpath=//div[contains(@class,'activity-distance-status')]//span[normalize-space()='Отправлено на проверку']"
        )
        expect(status).to_be_visible(timeout=30000)

    def start_edit_answer(self) -> None:
        """Второй участник группового ПЗ: разблокировать общий ответ для редактирования."""
        edit_button = self.page.get_by_role("button", name="Редактировать")
        expect(edit_button).to_be_visible(timeout=15000)
        expect(edit_button).to_be_enabled(timeout=15000)
        edit_button.click(timeout=5000)
        expect(self.answer_textarea).to_be_editable(timeout=15000)

    def edit_answer(self, text: str) -> None:
        self.answer_textarea.fill(text, timeout=5000)
        expect(self.answer_textarea).to_have_value(text, timeout=10000)
