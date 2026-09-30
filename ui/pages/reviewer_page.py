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

    def additional_materials_table(self) -> Locator:
        """Таблица файлов под подписью «Дополнительные материалы по заданию» на странице проверки
        (страница проверяющего: подпись `.coaches__label`, следом `.files-table`)."""
        return self.page.locator(
            "xpath=//div[contains(@class,'coaches__label') and contains(normalize-space(),'Дополнительные материалы')]"
            "/following-sibling::div[contains(@class,'files-table')][1]"
        )

    def additional_material_link(self, file_name: str) -> Locator:
        """Ссылка на скачивание файла доп. материалов по имени файла."""
        return self.additional_materials_table().locator("tr").filter(has_text=file_name).locator("a[download]")

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

    # ── Взаимопроверка (p2p): peer-проверки, агрегаты, итог, возврат ────
    # Функциональности ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_p2p.md,
    # docs/test_cases/p2p/06_final_result.md, 07_aggregation.md, 08_return_for_revision.md).
    # Селекторы ниже — предположение по аналогии с существующим блоком «Проверка ответа»
    # этого же файла (additional_materials_table/comment_textarea/select_grade).
    # TODO: уточнить после ветки — каждый локатор.

    def open_peer_reviews_block(self) -> None:
        """Блок всех peer-проверок по работе, видимый штатному проверяющему ПЗ
        (04 §9, §3 — роли)."""
        block = self.page.locator("xpath=//div[contains(@class,'peer-reviews-block')]")  # TODO: уточнить после ветки
        expect(block).to_be_visible(timeout=15000)

    def peer_review_rows(self) -> Locator:
        # TODO: уточнить после ветки — одна строка = одна peer-проверка одного проверяющего
        return self.page.locator("xpath=//div[contains(@class,'peer-reviews-block')]//tr[contains(@class,'vs-table__row')]")

    def peer_review_value(self, reviewer_full_name: str, criterion_label: str) -> Locator:
        # TODO: уточнить после ветки
        return self.page.locator(
            "xpath=//div[contains(@class,'peer-reviews-block')]"
            f"//tr[.//*[normalize-space()='{reviewer_full_name}']]"
            f"//td[@data-criterion='{criterion_label}']"
        )

    def aggregate_value(self, criterion_label: str) -> Locator:
        """Агрегированное значение по критерию: среднее с округлением до 0,1 для
        числовых критериев, список ответов для текстовых (04 §5.1)."""
        # TODO: уточнить после ветки
        return self.page.locator(
            "xpath=//div[contains(@class,'peer-review-aggregates')]"
            f"//div[contains(@class,'criterion') and contains(.,'{criterion_label}')]"
            "//*[contains(@class,'aggregate-value')]"
        )

    def expect_aggregate_value(self, criterion_label: str, expected: str) -> None:
        value = self.aggregate_value(criterion_label)
        expect(value).to_have_text(expected, timeout=15000)

    # ── Итоговый результат ────────────────────────────────────────────────

    def open_final_result_form(self) -> None:
        # TODO: уточнить после ветки
        button = self.page.get_by_role("button", name="Выставить итоговый результат")
        expect(button).to_be_visible(timeout=15000)
        button.click(timeout=5000)

    def set_final_result(self, grade: str) -> None:
        """Штатный проверяющий выставляет (или меняет) итоговый результат по работе
        (04 §9 п.1–2)."""
        self.select_grade(grade)
        submit_button = self.page.get_by_role("button", name="Сохранить итог")  # TODO: уточнить после ветки
        expect(submit_button).to_be_visible(timeout=15000)
        expect(submit_button).to_be_enabled(timeout=15000)
        submit_button.click(timeout=5000)

    def expect_final_result(self, grade: str) -> None:
        # TODO: уточнить после ветки
        result = self.page.locator(f"xpath=//div[contains(@class,'final-result') and contains(.,'{grade}')]")
        expect(result).to_be_visible(timeout=15000)

    def expect_final_result_action_unavailable(self) -> None:
        """Администратор без назначения штатным проверяющим не может выставить итоговый
        результат — просмотр работ/назначений/статистики остаётся доступен (04 §9, §3)."""
        # TODO: уточнить после ветки — либо кнопка не отрисована, либо disabled
        button = self.page.get_by_role("button", name="Выставить итоговый результат")
        expect(button).to_have_count(0)

    # ── Возврат на доработку ──────────────────────────────────────────────

    def return_for_revision(self, comment: str) -> None:
        """Возврат работы на доработку — доступно только штатному проверяющему ПЗ
        (04 §8.2 п.2; слушатель-проверяющий такого действия не видит, 03 §9)."""
        # TODO: уточнить после ветки
        button = self.page.get_by_role("button", name="Вернуть на доработку")
        expect(button).to_be_visible(timeout=15000)
        button.click(timeout=5000)

        comment_field = self.page.locator("xpath=//div[contains(@class,'v-dialog__content--active')]//textarea")
        expect(comment_field).to_be_visible(timeout=15000)
        comment_field.fill(comment, timeout=5000)

        confirm_button = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[normalize-space()='Вернуть']]"
        )
        confirm_button.click(timeout=5000)

    def expect_return_for_revision_unavailable(self) -> None:
        """Слушатель-проверяющий не должен видеть действие «Вернуть на доработку»
        (04 §8.2 п.2)."""
        # TODO: уточнить после ветки
        button = self.page.get_by_role("button", name="Вернуть на доработку")
        expect(button).to_have_count(0)

    def expect_returned_for_revision_mark(self) -> None:
        """Пометка «доработано» у повторно сданной после возврата работы (04 §8.2 п.6)."""
        # TODO: уточнить после ветки
        mark = self.page.locator("xpath=//span[normalize-space()='Доработано']")
        expect(mark).to_be_visible(timeout=15000)
