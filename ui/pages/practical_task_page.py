"""Слушатель проходит ПЗ: программа → «Курсы и тесты» → карточка ПЗ →
скачивание документов, ответ текстом и файлом, редактирование общего ответа
(групповое ПЗ вторым участником).

Перенос src/ui/locators/user_programs_locators.py коллеги
(репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re
from pathlib import Path
from typing import Iterable, Union

from playwright.sync_api import Page, Locator, Download, expect
from ui.pages.base_page import BasePage


class PracticalTaskPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_programs_list(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}/programs")

    def open_individual_education(self) -> None:
        """Раздел «Индивидуальное обучение» — ПЗ, назначенные пользователю напрямую (не через поток).
        На этом стенде это переключатель вкладки на странице «Моё обучение», а не отдельный
        роут — URL после клика не меняется, поэтому проверяем только видимость самого переключателя."""
        link = self.page.locator("text=Индивидуальное обучение").first
        expect(link).to_be_visible(timeout=15000)
        link.click(timeout=5000, force=True)

    def program_title(self, program_name: str) -> Locator:
        # Карточка программы на «Моё обучение» (/education, куда редиректит /programs):
        # заголовок — <a class="program-card__link">ИмяПрограммы</a>; у карточки есть ещё
        # такие же по классу ссылки "–" (даты) и "О программе" — отбираем по точному тексту.
        return self.page.locator("a.program-card__link").filter(has_text=re.compile(rf"^{re.escape(program_name)}$"))

    def open_program(self, program_name: str) -> None:
        expect(self.program_title(program_name).first).to_be_visible(timeout=30000)
        self.program_title(program_name).first.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/program.*"), timeout=30000)

    def open_courses_and_tests_tab(self) -> None:
        tab = self.page.locator("xpath=//span[normalize-space()='Курсы и тесты']")
        expect(tab).to_be_visible(timeout=15000)
        # force=True: вкладка Vuetify-таба, обычный клик иногда перехватывается соседней анимацией
        tab.click(timeout=5000, force=True)

    def practical_task_card(self, pz_name: Union[str, Iterable[str]]) -> Locator:
        # Карточка ПЗ показывается то под клиентским именем (name_client), то под
        # админским (name) — зависит от раздела (поток vs «Индивидуальное обучение»).
        # Принимаем одно или несколько возможных имён, матчим по любому совпадению.
        names = [pz_name] if isinstance(pz_name, str) else list(pz_name)
        predicate = " or ".join(f"contains(normalize-space(),'{name}')" for name in names)
        return self.page.locator(f"xpath=//div[contains(@class,'activity-card__title') and ({predicate})]").first

    def open_practical_task(self, pz_name: Union[str, Iterable[str]]) -> None:
        card = self.practical_task_card(pz_name)
        expect(card).to_be_visible(timeout=30000)
        card.click(timeout=5000)
        # Открытие ПЗ подтверждаем по панели деталей с названием задания, а не по
        # `?homework=<id>` в URL: когда туры раздела уже закрыты через API (07.10, ветка
        # Игоря), карточка оказывается выбранной сразу при загрузке, и клик по уже
        # выбранной карточке параметр в URL не дописывает — детали при этом открыты.
        names = [pz_name] if isinstance(pz_name, str) else list(pz_name)
        predicate = " or ".join(f"contains(normalize-space(),'{name}')" for name in names)
        details = self.page.locator(
            f"xpath=//div[contains(@class,'details__title') and ({predicate})]"
        ).first
        expect(details).to_be_visible(timeout=15000)

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

    # ── Взаимопроверка (p2p): «Работы на проверку» ──────────────────────
    # Функциональности ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_p2p.md,
    # docs/test_cases/p2p/04_peer_review.md). Все селекторы ниже — предположение по
    # аналогии с уже существующими блоками страницы (вкладки по normalize-space(),
    # карточки по activity-card__title) и с ui/pages/reviewer_page.py (та же
    # верхнеуровневая структура «список → открыть → форма → отправить»).
    # TODO: уточнить после ветки — каждый локатор и структура формы критериев.

    def open_peer_review_works_tab(self) -> None:
        """Раздел «Работы на проверку» слушателя-проверяющего (04 §3.1, §6.1) — только
        чужие назначенные работы, собственная работа не выводится."""
        tab = self.page.locator("xpath=//span[normalize-space()='Работы на проверку']")  # TODO: уточнить после ветки
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000, force=True)

    def peer_review_work_row(self, author_full_name: str) -> Locator:
        # TODO: уточнить после ветки — структура строки/карточки чужой работы
        return self.page.locator(
            f"xpath=//div[contains(@class,'activity-card') and contains(.,'{author_full_name}')]"
        )

    def open_peer_review_work(self, author_full_name: str) -> None:
        row = self.peer_review_work_row(author_full_name)
        expect(row).to_be_visible(timeout=30000)
        row.click(timeout=5000)

    # ── Форма критериев (03 §7.4: шкала / ОиМ / МиМ / текст) ────────────

    def select_scale_criterion_value(self, criterion_label: str, value: str) -> None:
        # TODO: уточнить после ветки — вероятно v-select/radio-группа по значению шкалы
        control = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{criterion_label}')]/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(control).to_be_visible(timeout=15000)
        control.click(timeout=5000)
        option = self.page.locator(f"xpath=//div[contains(@class,'v-menu__content')]//*[normalize-space()='{value}']").first
        expect(option).to_be_visible(timeout=10000)
        option.click(timeout=5000)

    def select_single_choice_criterion(self, criterion_label: str, option_text: str) -> None:
        # TODO: уточнить после ветки — критерий «Одиночный выбор» (ОиМ, 03 §7.6)
        option = self.page.locator(
            f"xpath=//fieldset[.//legend[contains(normalize-space(),'{criterion_label}')]]"
            f"//label[normalize-space()='{option_text}']"
        )
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

    def select_multiple_choice_criterion(self, criterion_label: str, option_texts: Iterable[str]) -> None:
        # TODO: уточнить после ветки — критерий «Множественный выбор» (МиМ, 03 §7.7)
        for option_text in option_texts:
            checkbox = self.page.locator(
                f"xpath=//fieldset[.//legend[contains(normalize-space(),'{criterion_label}')]]"
                f"//label[normalize-space()='{option_text}']"
            )
            expect(checkbox).to_be_visible(timeout=15000)
            checkbox.click(timeout=5000)

    def fill_text_criterion(self, criterion_label: str, text: str) -> None:
        # TODO: уточнить после ветки — критерий «Текстовое поле» (03 §7.8)
        field = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{criterion_label}')]/following::textarea[1]"
        )
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def save_peer_review(self) -> None:
        """Сохранить проверку без финального подтверждения — значения можно менять
        повторно (04 §8.1)."""
        # TODO: уточнить после ветки
        button = self.page.get_by_role("button", name="Сохранить")
        expect(button).to_be_visible(timeout=15000)
        button.click(timeout=5000)

    def confirm_peer_review(self) -> None:
        """Финальное подтверждение проверки — после этого редактирование должно быть
        заблокировано (04 §8.1)."""
        # TODO: уточнить после ветки — отдельная кнопка/чекбокс подтверждения
        button = self.page.get_by_role("button", name="Подтвердить")
        expect(button).to_be_visible(timeout=15000)
        button.click(timeout=5000)

    def expect_peer_review_locked(self) -> None:
        """После финального подтверждения обычное редактирование заблокировано —
        форма критериев должна быть недоступна для правки (04 §8.1)."""
        # TODO: уточнить после ветки — вероятно disabled-атрибут полей формы
        form = self.page.locator("xpath=//form[.//legend]")  # форма критериев
        expect(form).to_have_attribute("aria-disabled", "true", timeout=15000)

    # ── Результат по своей работе (автор видит итог и значения по критериям) ──

    def open_own_work_result(self) -> None:
        """Автор ПЗ смотрит статус/итог/значения по критериям своей сданной работы
        (04 §11, 10_author_view.md)."""
        # TODO: уточнить после ветки
        tab = self.page.locator("xpath=//span[normalize-space()='Результат проверки']")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000, force=True)

    def own_work_final_result(self) -> Locator:
        # TODO: уточнить после ветки
        return self.page.locator("xpath=//div[contains(@class,'peer-review-result')]//*[contains(@class,'final-result')]")

    def expect_own_work_status(self, status: str) -> None:
        status_locator = self.page.locator(
            "xpath=//div[contains(@class,'activity-distance-status')]"
            f"//span[normalize-space()='{status}']"
        )
        expect(status_locator).to_be_visible(timeout=30000)
