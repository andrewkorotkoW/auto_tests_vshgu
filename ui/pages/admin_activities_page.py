"""Админка → «База Активити»: создание ПЗ (тип, обложка, документы, категория,
преподаватель и проверяющий через мультиселект), поиск в таблице.

Перенос локаторов tests/ui/admin/practical_tasks/helpers/create_practical_task.py
и src/ui/locators/admin_activities_locators.py коллеги (репозиторий lms, feature/my-tests)
в наш Page Object. Стиль ожиданий — expect(...).to_be_visible/enabled, без is_visible()-опросов
и без networkidle/sleep.
"""
import re
from pathlib import Path
from typing import Iterable, Union

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminActivitiesPage(BasePage):
    PATH = "/admin/activities"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Список / навигация ──────────────────────────────────────────────

    def open_list(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url}{self.PATH}")
        expect(self.page.locator("xpath=//a[@href='/admin/activities/create']")).to_be_visible(timeout=15000)

    def open_create_form(self) -> None:
        create_button = self.page.locator("xpath=//a[@href='/admin/activities/create']")
        expect(create_button).to_be_visible(timeout=15000)
        create_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/activities/create.*"), timeout=15000)

    # ── Тип активности ───────────────────────────────────────────────────

    def select_type_homework(self) -> None:
        select_button = self.page.locator("xpath=//span[contains(text(),'Тип сущности')]")
        select_button.click(timeout=5000)
        homework_type = self.page.locator("xpath=//div[contains(@data-qa,'button__homework')]")
        expect(homework_type).to_be_visible(timeout=10000)
        homework_type.click(timeout=5000)

    # ── Обязательные поля ────────────────────────────────────────────────

    @property
    def name_field(self) -> Locator:
        return self.page.locator("xpath=//label[contains(text(),'Название в админке')]/following::input[@type='text'][1]")

    @property
    def external_name_field(self) -> Locator:
        return self.page.locator("xpath=//label[contains(text(),'Название на внешке')]/following::input[@type='text'][1]")

    @property
    def duration_field(self) -> Locator:
        return self.page.locator("xpath=//label[contains(text(),'Продолжительность')]/following::input[@type='text'][1]")

    @property
    def description_field(self) -> Locator:
        return self.page.locator("xpath=//div[contains(@class,'fr-element-scroll-visible')]")

    def fill_name(self, name: str) -> None:
        expect(self.name_field).to_be_visible(timeout=15000)
        self.name_field.fill(name, timeout=5000)

    def fill_external_name(self, external_name: str) -> None:
        expect(self.external_name_field).to_be_visible(timeout=15000)
        self.external_name_field.fill(external_name, timeout=5000)

    def fill_duration(self, duration: str = "1") -> None:
        expect(self.duration_field).to_be_visible(timeout=15000)
        self.duration_field.fill(duration, timeout=5000)

    def fill_description(self, text: str) -> None:
        expect(self.description_field).to_be_visible(timeout=15000)
        self.description_field.fill(text, timeout=5000)

    def select_first_category(self) -> None:
        """Открыть селект «Категория» и выбрать первый доступный вариант (недоступные исключены локатором)."""
        category_button = self.page.locator("xpath=//div[@role='button' and .//label[contains(text(),'Категория')]]")
        category_button.click(timeout=5000)

        overlay = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')][1]"
        )
        expect(overlay).to_be_visible(timeout=10000)

        options = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            "//div[contains(@class,'v-list-item') and not(contains(@class,'v-list-item--disabled'))]"
        )
        expect(options.first).to_be_visible(timeout=10000)
        options.first.click(timeout=5000)

    # ── Обложка и документы ──────────────────────────────────────────────

    def upload_cover(self, path: Union[str, Path]) -> None:
        cover_input = self.page.locator("xpath=//input[@accept='.jpeg,.jpg,.png']")
        cover_input.set_input_files(str(path))
        expect(self.page.locator("xpath=//div[contains(@class,'preview__img')]//img")).to_be_visible(timeout=15000)

    def upload_main_document(self, path: Union[str, Path]) -> None:
        self.page.locator("xpath=(//input[@accept='*'])[1]").set_input_files(str(path))
        self._wait_upload_complete()

    def upload_additional_document(self, path: Union[str, Path]) -> None:
        self.page.locator(
            "xpath=//span[contains(text(),'Добавить дополнительный документ')]/following::input[@class='file__input']"
        ).set_input_files(str(path))
        self._wait_upload_complete()

    def _wait_upload_complete(self) -> None:
        """Дождаться скрытия индикатора «Идет загрузка: N%» после set_input_files.
        Пока он виден, страница держит поверх модалок собственный overlay/scrim — если
        открыть модалку «Добавить преподавателей/проверяющих» до его исчезновения, клик
        по комбобоксу попадает в чужой scrim и модалка закрывается сама, не приняв ввод."""
        loader = self.page.get_by_text("Идет загрузка", exact=False)
        if loader.count():
            expect(loader.first).to_be_hidden(timeout=30000)

    # ── Преподаватель / проверяющий (мультиселект по ФИО) ───────────────

    def add_teacher(self, full_name: str) -> None:
        add_button = self.page.locator("xpath=(//button[contains(@class,'button-admin ma-0')])[1]")
        add_button.click(timeout=5000)

        modal = self.page.locator("xpath=//div[contains(@class,'v-dialog__content--active')]")
        expect(modal).to_be_visible(timeout=15000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//div[contains(@class,'v-input__slot') and @role='combobox']"
        )
        # Без force=True: пока не осела transition-анимация модалки, её scrim (z-index: auto,
        # pointer-events: auto) перехватывает клик поверх комбобокса (v-dialog__content--active
        # держит pointer-events: none, пока не станет активным) — обычный click дожидается,
        # пока цель реально начнёт принимать события, а не форсирует клик в перехватчик.
        select_field.click(timeout=15000)
        self.page.keyboard.type(full_name, delay=30)

        option = self._dropdown_option_by_text(full_name)
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

        modal_title = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//*[contains(text(),'Добавить преподавателей')]"
        )
        modal_title.click(timeout=3000)

        add_confirm = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[contains(text(),'Добавить')]]"
        )
        add_confirm.click(timeout=5000)
        # дождаться закрытия модалки — иначе клик по кнопке «Добавить» проверяющего может
        # попасть в ещё не отыгравшую transition закрытия модалки преподавателей
        expect(modal).to_be_hidden(timeout=15000)

    def add_reviewer(self, full_name: str) -> None:
        add_button = self.page.locator("xpath=(//button[contains(@class,'button-admin ma-0')])[2]")
        add_button.click(timeout=5000)

        modal_title = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//*[contains(text(),'Добавить проверяющих')]"
        )
        expect(modal_title).to_be_visible(timeout=15000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//label[normalize-space()='Проверяющий']/ancestor::div[contains(@class,'v-input')][1]"
        )
        # Без force=True — та же причина, что в add_teacher: пока scrim модалки не «остыл»
        # после transition, он перехватывает клик поверх комбобокса.
        select_field.click(timeout=15000)
        self.page.keyboard.type(full_name, delay=30)

        safe_name = full_name.replace("'", "")
        option = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            f"//div[@role='option' and .//*[contains(normalize-space(),'{safe_name}')]]"
        )
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

        modal_title.click(timeout=3000)

        add_confirm = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[normalize-space()='Добавить']]"
        )
        add_confirm.click(timeout=5000)

    def _dropdown_option_by_text(self, text: str) -> Locator:
        safe = text.replace("'", "")
        return self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            f"//div[@role='option' and .//*[contains(normalize-space(),'{safe}')]]"
        )

    # ── Сохранение / поиск ────────────────────────────────────────────────

    def save(self) -> None:
        radio_five_point = self.page.locator("xpath=//label[contains(text(),'Пятибалльная')]/preceding::input[@type='radio'][1]")
        expect(radio_five_point).to_be_checked(timeout=15000)

        save_button = self.page.locator("xpath=//button[.//span[contains(text(),'Сохранить')]]")
        save_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/activities.*"), timeout=30000)

    def search(self, name: str) -> None:
        search_input = self.page.locator("xpath=//input[contains(@placeholder,'Название активити')]")
        expect(search_input).to_be_visible(timeout=15000)
        search_input.fill(name, timeout=5000)
        search_input.press("Enter")

    def row_by_name(self, name: str) -> Locator:
        safe = name.replace("'", "")
        return self.page.locator(f"xpath=//table//tr[.//td[contains(normalize-space(),'{safe}')]]")

    def expect_created(self, name: str) -> None:
        self.search(name)
        expect(self.row_by_name(name)).to_be_visible(timeout=15000)

    def activity_id(self, name: str) -> int:
        """ID созданной активити — из href ссылки на неё в строке таблицы (после expect_created)."""
        link = self.row_by_name(name).locator("a[href*='/admin/activities/']").first
        href = link.get_attribute("href")
        return int(href.rstrip("/").split("/")[-1])

    # ── Композитный сценарий создания ПЗ ────────────────────────────────

    def create_homework_activity(
        self,
        *,
        name: str,
        external_name: str,
        cover_path: Union[str, Path],
        main_document_path: Union[str, Path],
        additional_document_path: Union[str, Path],
        teacher_full_name: str,
        reviewer_full_name: str,
        description: str = "Автотест: описание практического задания",
        duration: str = "1",
    ) -> None:
        """Полный сценарий создания ПЗ в «База Активити»: форма уже должна быть открыта
        (см. open_create_form()). Возвращает управление после сохранения и проверки в таблице."""
        self.select_type_homework()
        self.upload_cover(cover_path)
        self.fill_name(name)
        self.fill_external_name(external_name)
        self.fill_duration(duration)
        self.select_first_category()
        self.fill_description(description)
        self.upload_main_document(main_document_path)
        self.upload_additional_document(additional_document_path)
        self.add_teacher(teacher_full_name)
        self.add_reviewer(reviewer_full_name)
        self.save()
        self.expect_created(name)

    # ── Взаимопроверка (p2p): тумблер, штатные проверяющие, критерии ────
    # Функциональности ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_p2p.md,
    # docs/test_cases/p2p/00_pt_card_settings.md, 01_criteria.md). Методы — по аналогии
    # с add_teacher/add_reviewer этого же класса (мультиселект по ФИО через модалку).
    # TODO: уточнить после ветки — каждый локатор.

    @property
    def peer_review_toggle(self) -> Locator:
        return self.page.locator(
            "xpath=//label[contains(normalize-space(),'Включить взаимопроверку')]/following::input[@type='checkbox'][1]"
        )  # TODO: уточнить после ветки

    def enable_peer_review(self) -> None:
        """Включить тумблер «Включить взаимопроверку» — должен открыть блок
        дополнительных настроек (штатные проверяющие, форма критериев, 04 §4)."""
        expect(self.peer_review_toggle).to_be_visible(timeout=15000)
        self.peer_review_toggle.click(timeout=5000)

    def expect_peer_review_settings_visible(self) -> None:
        # TODO: уточнить после ветки
        block = self.page.locator("xpath=//div[contains(@class,'peer-review-settings')]")
        expect(block).to_be_visible(timeout=15000)

    def add_peer_reviewer(self, full_name: str) -> None:
        """Штатный проверяющий взаимопроверки (04 §4.2) — отдельный список от обычного
        проверяющего ПЗ (add_reviewer): назначение сюда должно автоматически выдавать
        роль «Преподаватель», если её ещё нет (04 §3.1)."""
        # TODO: уточнить после ветки — вероятно третья кнопка «button-admin ma-0» в блоке
        # взаимопроверки, по аналогии с add_teacher (первая)/add_reviewer (вторая)
        add_button = self.page.locator("xpath=(//button[contains(@class,'button-admin ma-0')])[3]")
        add_button.click(timeout=5000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//label[contains(normalize-space(),'Штатный проверяющий')]/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_field).to_be_visible(timeout=15000)
        select_field.click(timeout=15000)
        self.page.keyboard.type(full_name, delay=30)
        self.page.wait_for_timeout(800)

        safe_name = full_name.replace("'", "")
        option = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            f"//div[@role='option' and .//*[contains(normalize-space(),'{safe_name}')]]"
        )
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

        confirm_button = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[normalize-space()='Добавить']]"
        )
        confirm_button.click(timeout=5000)

    # ── Конструктор критериев (03 §7: шкала / ОиМ / МиМ / текст) ─────────
    # На этом этапе (кейсы до разработки) автотест не планируется — раздел manual,
    # методы нужны только для подготовки данных UI-тестами peer-проверки.

    def open_criteria_tab(self) -> None:
        tab = self.page.locator("xpath=//span[normalize-space()='Критерии']")  # TODO: уточнить после ветки
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000, force=True)

    def add_scale_criterion(self, label: str, options: Iterable[str], weight: int = 1) -> None:
        """Критерий «Шкала» — количество вариантов не ограничено диапазоном 1–10
        (03 §7.4–7.5)."""
        # TODO: уточнить после ветки
        add_button = self.page.get_by_role("button", name="Добавить критерий")
        add_button.click(timeout=5000)
        self.page.get_by_text("Шкала", exact=True).click(timeout=5000)
        self._fill_criterion_label(label)
        for option in options:
            self._add_criterion_option(option)
        self._fill_criterion_weight(weight)

    def add_single_choice_criterion(self, label: str, options: Iterable[str]) -> None:
        """Критерий «Одиночный выбор» (ОиМ, 03 §7.6)."""
        # TODO: уточнить после ветки
        add_button = self.page.get_by_role("button", name="Добавить критерий")
        add_button.click(timeout=5000)
        self.page.get_by_text("Одиночный выбор", exact=True).click(timeout=5000)
        self._fill_criterion_label(label)
        for option in options:
            self._add_criterion_option(option)

    def add_multiple_choice_criterion(self, label: str, options: Iterable[str]) -> None:
        """Критерий «Множественный выбор» (МиМ, 03 §7.7)."""
        # TODO: уточнить после ветки
        add_button = self.page.get_by_role("button", name="Добавить критерий")
        add_button.click(timeout=5000)
        self.page.get_by_text("Множественный выбор", exact=True).click(timeout=5000)
        self._fill_criterion_label(label)
        for option in options:
            self._add_criterion_option(option)

    def add_text_criterion(self, label: str) -> None:
        """Критерий «Текстовое поле» (03 §7.8) — не участвует в числовой агрегации."""
        # TODO: уточнить после ветки
        add_button = self.page.get_by_role("button", name="Добавить критерий")
        add_button.click(timeout=5000)
        self.page.get_by_text("Текстовое поле", exact=True).click(timeout=5000)
        self._fill_criterion_label(label)

    def _fill_criterion_label(self, label: str) -> None:
        # TODO: уточнить после ветки
        field = self.page.locator("xpath=(//label[contains(text(),'Название критерия')]/following::input[@type='text'])[last()]")
        expect(field).to_be_visible(timeout=15000)
        field.fill(label, timeout=5000)

    def _add_criterion_option(self, option_text: str) -> None:
        # TODO: уточнить после ветки
        add_option_button = self.page.get_by_role("button", name="Добавить вариант").last
        add_option_button.click(timeout=5000)
        option_field = self.page.locator("xpath=(//input[contains(@class,'criterion-option')])[last()]")
        option_field.fill(option_text, timeout=5000)

    def _fill_criterion_weight(self, weight: int) -> None:
        # TODO: уточнить после ветки
        field = self.page.locator("xpath=(//label[contains(text(),'Вес')]/following::input[@type='text'])[last()]")
        field.fill(str(weight), timeout=5000)

    def save_criteria(self) -> None:
        save_button = self.page.locator("xpath=//button[.//span[contains(text(),'Сохранить')]]")  # TODO: уточнить после ветки
        save_button.click(timeout=5000)

    def expect_add_criterion_unavailable(self) -> None:
        """После первой полученной peer-проверки нельзя добавить новый критерий
        (04 §5.2)."""
        # TODO: уточнить после ветки
        add_button = self.page.get_by_role("button", name="Добавить критерий")
        expect(add_button).to_be_disabled(timeout=15000)

    def expect_delete_criterion_unavailable(self, label: str) -> None:
        """После первой полученной peer-проверки нельзя удалить существующий критерий,
        но правка текста разрешена (04 §5.2)."""
        # TODO: уточнить после ветки
        delete_button = self.page.locator(
            f"xpath=//div[contains(@class,'criterion') and contains(.,'{label}')]//button[@aria-label='delete']"
        )
        expect(delete_button).to_have_count(0)
