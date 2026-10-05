"""Проверяющий: раздел «Практические задания» → поиск ПЗ на проверку (по потоку
или индивидуальному назначению) → скачивание ответа → комментарий и файл → оценка.

Перенос src/ui/locators/reviewer_homeworks_locators.py коллеги
(репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re
from pathlib import Path
from typing import Iterable, Union

from playwright.sync_api import Page, Locator, Download, expect
from ui.pages.base_page import BasePage


class ReviewerPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_practical_tasks_section(self) -> None:
        link = self.page.locator(
            "xpath=//div[contains(@class,'nav-item__wrapper') and .//span[normalize-space()='Практические задания']]"
        )
        expect(link).to_be_visible(timeout=15000)
        link.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/homeworks.*"), timeout=15000)

    # ── Поток ────────────────────────────────────────────────────────────

    @staticmethod
    def _name_predicate(pz_names: Union[str, Iterable[str]]) -> str:
        """Карточка/строка ПЗ в разных таблицах отображается то под клиентским именем
        (name_client), то под админским (name, без суффикса «_внешка_...») — см.
        group_pz_row_not_found_fix. Принимаем одно или несколько возможных имён и матчим
        строку, если совпало любое из них."""
        names = [pz_names] if isinstance(pz_names, str) else list(pz_names)
        return " or ".join(f"normalize-space()='{name}'" for name in names)

    def homework_row(self, user_full_name: str, program_name: str, stream_name: str, pz_name: Union[str, Iterable[str]]) -> Locator:
        return self.page.locator(
            "xpath=//tr[contains(@class,'vs-table__row')"
            f" and .//*[normalize-space()='{user_full_name}']"
            f" and .//*[normalize-space()='{program_name}']"
            f" and .//*[normalize-space()='{stream_name}']"
            f" and .//*[{self._name_predicate(pz_name)}]]"
        )

    def open_review(self, user_full_name: str, program_name: str, stream_name: str, pz_name: Union[str, Iterable[str]]) -> None:
        row = self.homework_row(user_full_name, program_name, stream_name, pz_name)
        expect(row).to_be_visible(timeout=30000)
        row.get_by_role("link", name="Проверить").click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/homeworks/\d+/answer/\d+.*"), timeout=15000)

    def expect_answered(self, user_full_name: str, program_name: str, stream_name: str, pz_name: Union[str, Iterable[str]], grade: str) -> None:
        row = self.page.locator(
            "xpath=//tr[contains(@class,'vs-table__row')"
            f" and .//*[normalize-space()='{user_full_name}']"
            f" and .//*[normalize-space()='{program_name}']"
            f" and .//*[normalize-space()='{stream_name}']"
            f" and .//*[{self._name_predicate(pz_name)}]"
            f" and .//*[normalize-space()='{grade}']]"
        )
        expect(row).to_be_visible(timeout=30000)

    # ── Индивидуальное назначение ────────────────────────────────────────

    def personal_homework_row(self, user_full_name: str, pz_name: Union[str, Iterable[str]]) -> Locator:
        return self.page.locator(
            "xpath=//tr[contains(@class,'vs-table__row')"
            f" and .//*[normalize-space()='{user_full_name}']"
            f" and .//*[{self._name_predicate(pz_name)}]]"
        )

    def open_personal_review(self, user_full_name: str, pz_name: Union[str, Iterable[str]]) -> None:
        row = self.personal_homework_row(user_full_name, pz_name)
        expect(row).to_be_visible(timeout=30000)
        row.get_by_role("link", name="Проверить").click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/homeworks/\d+/answer/\d+.*"), timeout=15000)

    def expect_personal_answered(self, user_full_name: str, pz_name: Union[str, Iterable[str]], grade: str) -> None:
        row = self.page.locator(
            "xpath=//tr[contains(@class,'vs-table__row')"
            f" and .//*[normalize-space()='{user_full_name}']"
            f" and .//*[{self._name_predicate(pz_name)}]"
            f" and .//*[normalize-space()='{grade}']]"
        )
        expect(row).to_be_visible(timeout=30000)

    # ── Проверка ответа (общая для потока и индивидуального ПЗ) ─────────

    @property
    def user_answer_download_button(self) -> Locator:
        return self.page.locator("xpath=(//a[@download])[last()]")

    def download_user_answer(self) -> Download:
        expect(self.user_answer_download_button).to_be_visible(timeout=15000)
        with self.page.expect_download(timeout=15000) as download_info:
            self.user_answer_download_button.click(timeout=5000)
        return download_info.value

    @property
    def comment_textarea(self) -> Locator:
        return self.page.locator("xpath=//label[normalize-space()='Поле ввода ответа']/following::textarea[contains(@class,'v-field__input')][1]")

    def fill_comment(self, text: str) -> None:
        expect(self.comment_textarea).to_be_visible(timeout=15000)
        self.comment_textarea.fill(text, timeout=5000)

    def attach_review_file(self, path: Union[str, Path]) -> None:
        attach_button = self.page.get_by_role("button", name="Прикрепить файл")
        expect(attach_button).to_be_visible(timeout=15000)
        with self.page.expect_file_chooser(timeout=15000) as file_chooser_info:
            attach_button.click(timeout=5000)
        file_chooser_info.value.set_files(str(path))

    def select_grade(self, grade: str) -> None:
        grade_select = self.page.locator("xpath=//label[normalize-space()='Оценка']/ancestor::div[contains(@class,'v-input')][1]")
        expect(grade_select).to_be_visible(timeout=15000)
        grade_select.click(timeout=5000)

        option = self.page.locator(
            f"xpath=//div[contains(@class,'v-overlay') or contains(@class,'v-menu')]//*[normalize-space()='{grade}']"
        ).first
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

    def submit_review(self) -> None:
        submit_button = self.page.get_by_role("button", name="Отправить").first
        expect(submit_button).to_be_visible(timeout=15000)
        expect(submit_button).to_be_enabled(timeout=15000)
        submit_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/homeworks.*"), timeout=30000)

    def open_answered_tab(self) -> None:
        tab = self.page.locator("xpath=//div[contains(@class,'tab-list__item')][.//span[normalize-space()='Отвечено']]")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)

    def review(self, *, comment: str, file_path: Union[str, Path], grade: str) -> None:
        """Композитный флоу проверки: комментарий, файл, оценка, отправка."""
        self.fill_comment(comment)
        self.attach_review_file(file_path)
        self.select_grade(grade)
        self.submit_review()
