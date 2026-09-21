"""Админка: программа → поток (все обязательные селекты) → модуль,
добавление активити в расписание модуля, добавление слушателя на поток.

Перенос src/ui/locators/admin_programs_locators.py и
tests/ui/admin/practical_tasks/helpers/{module_schedule,stream_listeners,navigation}.py
коллеги (репозиторий lms, feature/my-tests) в наш Page Object.
"""
import re
from typing import Union

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminProgramsPage(BasePage):
    PATH = "/admin/programs"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Программа ────────────────────────────────────────────────────────

    def open_list(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url}{self.PATH}")

    def open_programs_link(self) -> None:
        link = self.page.locator("xpath=//a[@href='/admin/programs' and contains(@class,'menu__item')]")
        expect(link).to_be_visible(timeout=15000)
        link.click(timeout=5000)

    def open_create_program_form(self) -> None:
        create_button = self.page.locator("xpath=//a[contains(@href,'/admin/programs/create')]")
        expect(create_button).to_be_visible(timeout=15000)
        create_button.click(timeout=5000)

    def fill_program_name(self, name: str) -> None:
        field = self.page.locator("xpath=//textarea[@rows='2']")
        expect(field).to_be_visible(timeout=15000)
        field.fill(name, timeout=5000)

    def fill_program_description(self, text: str) -> None:
        field = self.page.locator("xpath=//div[contains(@class,'fr-element')]")
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def save_program(self) -> None:
        save_button = self.page.locator("xpath=//button[contains(@class,'button-admin--ocean')]")
        expect(save_button).to_be_visible(timeout=15000)
        expect(save_button).to_be_enabled(timeout=15000)
        save_button.click(timeout=15000)
        expect(self.page.locator("xpath=//span[contains(text(),'Название Программы')]")).to_be_visible(timeout=15000)

    def search_program(self, name: str) -> None:
        search_input = self.page.locator("xpath=//input[@placeholder='Поиск']")
        expect(search_input).to_be_visible(timeout=15000)
        search_input.fill(name, timeout=5000)
        search_input.press("Enter")

    def program_row(self, name: str) -> Locator:
        safe = name.replace("'", "")
        return self.page.locator(f"xpath=//tr[.//a[contains(@href,'/admin/programs/')]/span[normalize-space()='{safe}']]")

    def open_program(self, name: str) -> int:
        """Открыть программу по имени (после search_program) и вернуть её id."""
        expect(self.program_row(name)).to_be_visible(timeout=15000)
        self.program_row(name).locator("a").first.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/admin/programs/\d+.*"), timeout=30000)
        return int(self.page.url.rstrip("/").split("/")[-1])

    def create_program(self, name: str, description: str = "Автотест: описание программы") -> None:
        self.open_programs_link()
        self.open_create_program_form()
        self.fill_program_name(name)
        self.fill_program_description(description)
        self.save_program()
        self.search_program(name)
        expect(self.program_row(name)).to_be_visible(timeout=15000)

    # ── Поток ────────────────────────────────────────────────────────────

    def open_create_stream_form(self) -> None:
        create_button = self.page.locator(
            "xpath=//a[contains(@href,'/streams/create') and contains(normalize-space(), 'Создать')]"
        )
        expect(create_button).to_be_visible(timeout=15000)
        create_button.click(timeout=5000)
        expect(self.page).to_have_url(re.compile(r".*/streams/create.*"), timeout=30000)

    def fill_stream_basic_fields(self, name: str, place: str, date_from: str, date_to: str) -> None:
        name_field = self.page.locator("xpath=//label[contains(text(),'Название потока')]/following::input[@type='text'][1]")
        expect(name_field).to_be_visible(timeout=15000)
        name_field.fill(name, timeout=5000)

        place_field = self.page.locator("xpath=//label[contains(text(),'Место проведения')]/following::input[@type='text'][1]")
        expect(place_field).to_be_visible(timeout=15000)
        place_field.fill(place, timeout=5000)

        date_from_field = self.page.locator("xpath=//label[contains(text(),'Дата проведения с')]/following::input[@type='text'][1]")
        expect(date_from_field).to_be_visible(timeout=15000)
        date_from_field.fill(date_from, timeout=5000)

        date_to_field = self.page.locator("xpath=//label[contains(text(),'Дата проведения по')]/following::input[@type='text'][1]")
        expect(date_to_field).to_be_visible(timeout=15000)
        date_to_field.fill(date_to, timeout=5000)

    def _add_user_via_modal(self, add_button: Locator) -> None:
        """Общий флоу модалки «Добавить менеджера»: открыть, выбрать первого пользователя, подтвердить."""
        expect(add_button).to_be_visible(timeout=15000)
        add_button.click(timeout=5000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//input[@type='text' and not(@disabled)]"
        )
        expect(select_field).to_be_visible(timeout=15000)
        # force=True: поле открывается вместе с анимацией модалки, обычный клик может не успеть
        select_field.click(timeout=5000, force=True)

        first_user = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            "//div[contains(@class,'v-list-item') and not(contains(@class,'disabled'))]"
        ).first
        expect(first_user).to_be_visible(timeout=15000)
        first_user.click(timeout=5000)

        modal_title = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//div[contains(@class,'display-3') and normalize-space()='Добавить Менеджера']"
        )
        modal_title.click(timeout=5000)

        confirm_button = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[contains(normalize-space(),'Добавить')]]"
        )
        expect(confirm_button).to_be_enabled(timeout=15000)
        confirm_button.click(timeout=5000)

    def add_manager(self) -> None:
        button = self.page.locator("xpath=(//span[contains(text(),'Добавить менеджера')]/ancestor::button)[1]")
        self._add_user_via_modal(button)

    def add_external_manager(self) -> None:
        button = self.page.locator("xpath=(//span[contains(text(),'Добавить менеджера')]/ancestor::button)[2]")
        self._add_user_via_modal(button)

    def _select_first_dropdown_item(self, select_locator: Locator) -> None:
        expect(select_locator).to_be_visible(timeout=15000)
        # force=True: Vuetify-комбобокс, стандартный клик иногда перехватывается overlay-подложкой
        select_locator.click(timeout=5000, force=True)
        dropdown_items = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            "//div[contains(@class,'v-list-item__content')]"
        )
        expect(dropdown_items.first).to_be_visible(timeout=15000)
        dropdown_items.first.click(timeout=5000)

    def select_project(self) -> None:
        self._select_first_dropdown_item(self.page.get_by_role("textbox", name="Проект"))

    def select_academic_director(self) -> None:
        self._select_first_dropdown_item(
            self.page.locator(
                "xpath=//label[contains(normalize-space(),'Академический директор программы')]"
                "/ancestor::div[contains(@class,'v-input')][1]"
            )
        )

    def fill_expert_name(self, text: str) -> None:
        field = self.page.locator("xpath=//label[contains(text(),'Наименование для АИС')]/following::input[@type='text'][1]")
        expect(field).to_be_visible(timeout=15000)
        field.fill(text, timeout=5000)

    def select_cost_program_group(self) -> None:
        self._select_first_dropdown_item(self.page.get_by_role("textbox", name="Стоимостная группа"))

    def select_unit(self) -> None:
        self._select_first_dropdown_item(self.page.get_by_role("textbox", name="Подразделение реализации"))

    def select_program_type(self) -> None:
        self._select_first_dropdown_item(self.page.get_by_role("textbox", name="Вид программы"))

    def select_program_form(self) -> None:
        self._select_first_dropdown_item(self.page.get_by_role("textbox", name="Форма реализации"))

    def fill_total_load(self, value: str = "100") -> None:
        field = self.page.locator("xpath=//label[contains(text(),'Общий объем')]/following::input[@type='text'][1]")
        expect(field).to_be_visible(timeout=15000)
        field.fill(value, timeout=5000)
        self.page.keyboard.press("Escape")

    def save_stream(self) -> int:
        save_button = self.page.locator("xpath=//button[.//span[normalize-space()='Сохранить']]")
        expect(save_button).to_be_visible(timeout=15000)
        expect(save_button).to_be_enabled(timeout=15000)
        save_button.click(timeout=15000)
        expect(self.page).to_have_url(re.compile(r".*/admin/programs/\d+/streams/\d+.*"), timeout=30000)
        return int(self.page.url.rstrip("/").split("/")[-1])

    def create_stream(
        self,
        *,
        name: str,
        place: str,
        date_from: str,
        date_to: str,
        expert_name: str,
        total_load: str = "100",
    ) -> int:
        """Полный сценарий создания потока со всеми обязательными селектами.
        Возвращает stream_id. Форма создания потока должна быть уже открыта
        (см. open_create_stream_form())."""
        self.fill_stream_basic_fields(name, place, date_from, date_to)
        self.add_manager()
        self.add_external_manager()
        self.select_project()
        self.select_academic_director()
        self.fill_expert_name(expert_name)
        self.select_cost_program_group()
        self.select_unit()
        self.select_program_type()
        self.select_program_form()
        self.fill_total_load(total_load)
        return self.save_stream()

    # ── Модуль ───────────────────────────────────────────────────────────

    def open_schedule_tab(self) -> None:
        tab = self.page.locator("a.courses-list-tabs__item", has_text="Расписание")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)

    def create_module(self, name: str, place: str, start_date: str, finish_date: str) -> None:
        add_button = self.page.locator("xpath=//button[contains(@class,'v-btn--is-elevated')]")
        expect(add_button).to_be_visible(timeout=15000)
        add_button.click(timeout=5000)

        modal = self.page.locator("xpath=//div[contains(@class,'confirm v-card')]")
        expect(modal).to_be_visible(timeout=15000)

        name_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog')]//label[contains(text(),'Название Модуля')]/following-sibling::input"
        )
        expect(name_field).to_be_visible(timeout=15000)
        name_field.fill(name, timeout=5000)

        place_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog')]//label[contains(text(),'Место проведения')]/following-sibling::input"
        )
        expect(place_field).to_be_visible(timeout=15000)
        place_field.fill(place, timeout=5000)

        start_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog')]//label[contains(text(),'Начало')]/following::input[@type='text'][1]"
        )
        expect(start_field).to_be_visible(timeout=15000)
        start_field.fill(start_date, timeout=5000)

        finish_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog')]//label[contains(text(),'Окончание')]/following::input[@type='text'][1]"
        )
        expect(finish_field).to_be_visible(timeout=15000)
        finish_field.fill(finish_date, timeout=5000)

        save_button = self.page.locator("xpath=//*[@id='app']//button[.//span[normalize-space()='Применить']]")
        expect(save_button).to_be_visible(timeout=15000)
        expect(save_button).to_be_enabled(timeout=15000)
        save_button.click(timeout=5000)

        expect(self.page.locator("xpath=//div[text()='Модуль создан.']")).to_be_visible(timeout=15000)

    # ── Расписание модуля: добавление активити ──────────────────────────

    def add_activity_to_schedule(self, pz_name: str) -> None:
        add_activity_button = self.page.get_by_role("button", name="Добавить Активити")
        expect(add_activity_button).to_be_visible(timeout=15000)
        expect(add_activity_button).to_be_enabled(timeout=15000)
        add_activity_button.click(timeout=5000)

        modal = self.page.locator("xpath=//div[contains(@class,'v-dialog__content--active')]")
        expect(modal).to_be_visible(timeout=15000)

        clear_button = self.page.locator("xpath=//div[contains(@class,'v-dialog__content--active')]//button[contains(@aria-label,'Clear')]")
        if clear_button.count() > 0:
            clear_button.click(timeout=5000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//label[normalize-space()='Введите название или выберите из списка']"
            "/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_field).to_be_visible(timeout=15000)
        # force=True: комбобокс внутри модалки, добавления событий модалки перехватывают обычный клик
        select_field.click(timeout=5000, force=True)
        self.page.keyboard.type(pz_name, delay=30)

        safe = pz_name.replace("'", "")
        activity_item = self.page.locator(
            "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
            f"//div[@role='option' and .//*[contains(normalize-space(),'{safe}')]]"
        )
        expect(activity_item).to_be_visible(timeout=15000)
        activity_item.click(timeout=5000)

        modal_title = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//div[contains(@class,'display-3') and normalize-space()='Добавить']"
        )
        expect(modal_title).to_be_visible(timeout=15000)
        modal_title.click(timeout=5000)

        add_confirm = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[normalize-space()='Добавить']]"
        )
        expect(add_confirm).to_be_visible(timeout=15000)
        expect(add_confirm).to_be_enabled(timeout=15000)
        add_confirm.click(timeout=5000)

        expect(self._activity_in_schedule(pz_name)).to_be_visible(timeout=15000)

    def _activity_in_schedule(self, activity_name: str) -> Locator:
        safe = activity_name.replace("'", "")
        return self.page.locator(f"xpath=//tr[.//a[contains(@href,'/admin/activities/')]/span[normalize-space()='{safe}']]")

    # ── Слушатели потока ─────────────────────────────────────────────────

    def open_listeners_tab(self) -> None:
        tab = self.page.locator("a.courses-list-tabs__item", has_text="Слушатели")
        expect(tab).to_be_visible(timeout=15000)
        tab.click(timeout=5000)

    def add_listener(self, user_full_name: str, user_id: Union[int, str]) -> None:
        add_button = self.page.get_by_role("button", name="Добавить Слушателей")
        expect(add_button).to_be_visible(timeout=15000)
        expect(add_button).to_be_enabled(timeout=15000)
        add_button.click(timeout=5000)

        select_field = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]"
            "//label[normalize-space()='Выберите Пользователя']/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_field).to_be_visible(timeout=15000)
        # force=True: комбобокс модалки, ввод текста должен начаться сразу после клика по анимированному полю
        select_field.click(timeout=5000, force=True)
        self.page.keyboard.type(user_full_name, delay=80)

        option = self.page.locator(
            "xpath=//div[contains(@class,'menuable__content__active')]"
            f"//*[contains(normalize-space(),'{user_full_name}')]"
        ).first
        expect(option).to_be_visible(timeout=15000)
        option.click(timeout=5000)

        modal_title = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//*[contains(@class,'display-3')]"
        ).first
        expect(modal_title).to_be_visible(timeout=15000)
        modal_title.click(timeout=5000)

        confirm_button = self.page.locator(
            "xpath=//div[contains(@class,'v-dialog__content--active')]//button[.//span[normalize-space()='Добавить']]"
        )
        expect(confirm_button).to_be_enabled(timeout=15000)
        confirm_button.click(timeout=5000)

        expect(self.listener_row(user_id)).to_be_visible(timeout=30000)

    def listener_row(self, user_id: Union[int, str]) -> Locator:
        return self.page.locator(f"xpath=//a[contains(@href,'/admin/users/{user_id}')]")
