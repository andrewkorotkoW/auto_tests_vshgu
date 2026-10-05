"""Общая база для page-объектов админки хелпдеска
(https://helpdesk-develop.d2.devspark.ru/admin/*) — отдельный Laravel Backpack
хост, не связанный с Vue-админкой портала (другие ui/pages/admin_*_page.py).

Общий шаблон списка подтверждён разведкой (docs/helpdesk_recon.md) для всех
разделов: таблица на jQuery DataTables (`#crudTable`), кнопка «Добавить …»
(href="{path}/create"), в каждой строке — иконки действий с
`data-button-type="show"/"update"/"delete"` (Laravel Backpack, функция
`deleteEntry(this)` на удаление).

ВАЖНО: точный текст модалки подтверждения удаления группы/шаблона разведке
зафиксировать не удалось надёжно (клики в headless ловили общий текст модалки
для другого действия — см. docs/helpdesk_recon.md §6) — не хардкодить текст
модалки, проверять только факт её появления и наличие кнопок подтверждения.
"""
import re

from playwright.sync_api import Locator, expect

from ui.pages.base_page import BasePage

# Кнопка подтверждения удаления — текст варьируется («Удалить»/«Да» в разных
# модалках Backpack), поэтому матчим любой из двух вариантов одним regex.
DELETE_CONFIRM_BUTTON_RE = re.compile(r"^(Удалить|Да)$")


class HelpdeskAdminPage(BasePage):
    PATH = ""  # переопределить в наследнике, например "/admin/group"

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}")
        self.wait_loaded()

    @property
    def table(self) -> Locator:
        return self.page.locator("#crudTable")

    def row(self, text: str) -> Locator:
        """Строка таблицы списка, содержащая текст (например название/email)."""
        safe = text.replace("'", "")
        return self.page.locator(f"#crudTable tbody tr:has-text('{safe}')").first

    def open_create_form(self) -> None:
        self.page.locator(f"a[href$='{self.PATH}/create']").first.click()
        self.wait_loaded()

    def submit_form(self) -> None:
        """Сабмит текущей открытой формы создания/редактирования."""
        self.page.locator("button[type=submit], input[type=submit]").first.click()
        self.wait_loaded()

    def delete_row(self, text: str) -> None:
        """Удалить строку списка через иконку-корзину с подтверждением в модалке.

        Текст модалки не проверяем (см. докстринг модуля) — только факт её
        появления и клик по кнопке подтверждения ("Удалить"/"Да")."""
        row = self.row(text)
        expect(row).to_be_visible(timeout=15000)
        row.locator("[data-button-type='delete']").first.click()
        confirm_button = self.page.get_by_role("button", name=DELETE_CONFIRM_BUTTON_RE)
        expect(confirm_button).to_be_visible(timeout=15000)
        confirm_button.click()
        self.wait_hidden(row)
