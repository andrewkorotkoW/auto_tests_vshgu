"""Админка → «Справочники»: раскрывающийся пункт бокового меню со списком подстраниц —
каждая подстраница управляет одним типом справочника из общего REST-ресурса /dictionaries
(см. api/endpoints/dictionaries.py и docs/plans/2026-09-25_dictionaries_mission.md).

Раздел ЕСТЬ в боковом меню, но предыдущая разведка (docs/plans/2026-09-25_dictionaries_mission.md)
его не нашла: у пункта «Справочники» нет своего href — это `<div class="v-list-item__title">`,
раскрывающий вложенный список ссылок по клику (Vuetify v-list-group), а не `<a class="menu__item">`,
как у остальных пунктов, поэтому обход только по ссылкам (`AdminPage.go_to_admin()`) его не видел.
Проверено вручную на develop (25.09.2026): клик по заголовку раскрывает 6 ссылок:

    program_type       /admin/catalogs/programs        «Вид программы»
    learning_format     /admin/catalogs/forms           «Форма реализации»
    program_department  /admin/catalogs/departments     «Подразделение реализации»
    region               /admin/catalogs/regions         «Регионы»
    municipality          /admin/catalogs/municipalities  «Муниципалитеты»
    tag                   /admin/catalogs/test-themes      «Темы вопросов»

Типов `project` («Проект») и `program_level` («Стоимостная группа») среди подстраниц нет —
эти два типа управляются только через API, отдельной формы в админке для них не существует
(подтверждено обходом всех 6 ссылок подменю).

Каждая подстраница — одинаковый шаблон (проверено на program_type, полный round-trip
создание/редактирование/удаление вручную через этот Page Object на develop):
  - таблица .v-data-table с колонками «Значение»/«Действия»;
  - кнопка «Добавить …» открывает модалку с одним полем «Введите название» и кнопками
    «Отмена»/«Сохранить» (диз­эйблена, пока поле пустое);
  - в каждой строке таблицы — две кнопки-иконки: карандаш (редактирование, та же модалка,
    предзаполненная текущим значением) и корзина (удаление — модалка-подтверждение
    «Вы точно хотите удалить?» с кнопками «Отмена»/«Да»).
"""
from typing import List

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminDictionariesPage(BasePage):
    PATHS = {
        "program_type": "/admin/catalogs/programs",
        "learning_format": "/admin/catalogs/forms",
        "program_department": "/admin/catalogs/departments",
        "region": "/admin/catalogs/regions",
        "municipality": "/admin/catalogs/municipalities",
        "tag": "/admin/catalogs/test-themes",
    }

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str, dictionary_type: str) -> None:
        """Прямой переход на подстраницу типа справочника по URL. Строки таблицы приходят
        отдельным GET /api/v1/dictionaries?filters[type]=… уже после монтирования SPA и
        скелетона (разведка 13.10.2026) — ждём сам ответ, иначе values() читает пустую
        таблицу."""
        with self.page.expect_response(
            lambda r: "/api/v1/dictionaries?" in r.url and "filters%5Btype%5D=" in r.url,
            timeout=30000,
        ):
            self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATHS[dictionary_type]}")
        self.wait_loaded()

    def open_via_menu(self, dictionary_type: str) -> None:
        """Навигация из уже открытой админки (после AdminPage.go_to_admin()): развернуть
        группу «Справочники» в боковом меню и перейти по ссылке нужного типа."""
        menu_group = self.page.locator(
            "xpath=//div[contains(@class,'v-list-item__title') and normalize-space()='Справочники']"
        )
        expect(menu_group).to_be_visible(timeout=15000)
        menu_group.click(timeout=5000)

        link = self.page.locator(f"a[href='{self.PATHS[dictionary_type]}']")
        expect(link).to_be_visible(timeout=15000)
        self.click_and_wait(link)

    @property
    def table(self) -> Locator:
        return self.page.locator(".v-data-table").first

    def values(self) -> List[str]:
        """Значения текущей страницы таблицы (без учёта пагинации)."""
        return self.table.locator("tbody tr td:first-child").all_inner_texts()

    def row(self, value: str) -> Locator:
        safe = value.replace("'", "")
        return self.page.locator(f"xpath=//tr[td[1][normalize-space()='{safe}']]")

    def add_button(self) -> Locator:
        return self.page.locator("button", has_text="Добавить").first

    def _submit_name_modal(self, trigger: Locator, name: str) -> Locator:
        trigger.click(timeout=5000)
        modal = self.page.locator(".v-dialog--active").first
        expect(modal).to_be_visible(timeout=15000)

        input_el = modal.locator("input[type='text']").first
        expect(input_el).to_be_visible(timeout=15000)
        input_el.fill(name, timeout=5000)

        save_button = modal.locator("button", has_text="Сохранить")
        expect(save_button).to_be_enabled(timeout=15000)
        save_button.click(timeout=5000)
        return modal

    def create_item(self, name: str) -> None:
        """Создать элемент справочника через модалку «Добавить …»."""
        self._submit_name_modal(self.add_button(), name)
        expect(self.row(name)).to_be_visible(timeout=15000)

    def edit_item(self, current_name: str, new_name: str) -> None:
        """Отредактировать элемент справочника (карандаш в строке — первая кнопка действий)."""
        row = self.row(current_name)
        expect(row).to_be_visible(timeout=15000)
        edit_button = row.locator("button").nth(0)
        self._submit_name_modal(edit_button, new_name)
        expect(self.row(new_name)).to_be_visible(timeout=15000)

    def delete_item(self, name: str) -> None:
        """Удалить элемент справочника (корзина в строке — вторая кнопка действий) с
        подтверждением в модалке «Вы точно хотите удалить?» (кнопка «Да»)."""
        row = self.row(name)
        expect(row).to_be_visible(timeout=15000)
        delete_button = row.locator("button").nth(1)
        delete_button.click(timeout=5000)

        confirm_modal = self.page.locator(".v-dialog--active").first
        expect(confirm_modal).to_be_visible(timeout=15000)
        confirm_button = confirm_modal.get_by_role("button", name="Да", exact=True)
        expect(confirm_button).to_be_visible(timeout=15000)
        confirm_button.click(timeout=5000)

        self.wait_hidden(row)
