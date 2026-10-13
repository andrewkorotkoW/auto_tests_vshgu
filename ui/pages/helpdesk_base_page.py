"""Общая база для page-объектов админки хелпдеска
(https://helpdesk-develop.d2.devspark.ru/admin/*) — отдельный Laravel Backpack
хост, не связанный с Vue-админкой портала (другие ui/pages/admin_*_page.py).

Общий шаблон списка подтверждён разведкой (docs/helpdesk_recon.md) для всех
разделов: таблица на jQuery DataTables, кнопка «Добавить …»
(href="{path}/create"), в каждой строке — иконки действий с
`data-button-type="show"/"update"/"delete"` (Laravel Backpack, функция
`deleteEntry(this)` на удаление).

Локатор таблицы: `id` реального `<table>` со строками — статический `#crudTable`
только на /admin/mail-template, на остальных 4 из 5 списочных разделов —
динамический хеш-суффикс (`crudTable_<hash>`, подтверждено живым прогоном
Playwright на develop). Каждая страница списка рендерит ТРИ `<table
class="dataTable">` (jQuery DataTables рисует пустые header/footer-клоны для
горизонтального скролла) — у настоящей, со строками, всегда есть `tbody tr`,
у клонов `tbody` пустой. `table`/`row()` ищут по классу `table.dataTable`, а
не по id — устойчиво на всех разделах.

Поля форм создания/редактирования: `<label>` НЕ связан с `<input>` ни через
`for`/`id`, ни через обёртку (просто соседний элемент в одном
`[bp-field-wrapper]`-диве) — `page.get_by_label(...)` находит 0 элементов на
любой форме хелпдеска. Атрибут `bp-field-name` (реальное имя поля формы
Backpack, например `ticket_prefix`/`value`/`content`) на обёртке — устойчивый
якорь, `field()` ищет видимый control (input/select/textarea) внутри неё.

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

    # DataTables в Backpack — server-side: после загрузки страницы списка (и после
    # редиректа с сабмита формы) строки дотягиваются отдельным POST …/search, а таблица
    # на это время затемнена. Разведка develop 13.10.2026: проверка строки между
    # отправкой этого запроса и ответом видела старый список (test_dictionary_crud).
    # Поэтому open()/submit_form() ждут сам ответ /search, а не косвенные признаки.
    @staticmethod
    def _is_table_search(response) -> bool:
        return response.request.method == "POST" and response.url.split("?")[0].endswith("/search")

    def open(self, ui_base_url: str) -> None:
        with self.page.expect_response(self._is_table_search, timeout=30000):
            self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}")
        self.wait_loaded()

    @property
    def table(self) -> Locator:
        """Реальная (не header/footer-клон) таблица списка — единственная с непустым tbody."""
        return self.page.locator("table.dataTable:has(tbody tr)").first

    def row(self, text: str) -> Locator:
        """Строка таблицы списка, содержащая текст (например название/email).

        Матчит не весь текст целиком, а первые 30 символов: сервер обрезает длинные
        значения в ячейках многоточием при отображении (подтверждено живым прогоном —
        `:has-text()` с полным сгенерированным именем, например
        "Автотест_шаблон_master_<ts>", не находил только что созданную строку, потому
        что в ячейке реально "Автотест_шаблон_master_179124773…" — обрезка на 32-м
        символе). 30 — с небольшим запасом ниже этой границы, но максимально близко к
        ней, чтобы сохранить побольше цифр временной метки для уникальности между
        параллельными тестами (сам timestamp — хвост строки, за которым жертвовать
        нельзя)."""
        safe = text[:30].replace("'", "")
        return self.page.locator(f"table.dataTable tbody tr:has-text('{safe}')").first

    def field(self, bp_field_name: str) -> Locator:
        """Поле формы по реальному атрибуту `bp-field-name` (устойчиво к несвязанным
        label/input — см. докстринг модуля). Подходит для create- и edit-форм."""
        return self.page.locator(
            f'[bp-field-name="{bp_field_name}"] input, '
            f'[bp-field-name="{bp_field_name}"] select, '
            f'[bp-field-name="{bp_field_name}"] textarea'
        ).first

    def open_create_form(self) -> None:
        self.page.locator(f"a[href$='{self.PATH}/create']").first.click()
        self.wait_loaded()

    def submit_form(self) -> None:
        """Сабмит текущей открытой формы создания/редактирования: POST формы → 302 на
        список → DataTables подгружает строки POST …/search — ждём его ответ."""
        with self.page.expect_response(self._is_table_search, timeout=30000):
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
        # После подтверждения Backpack удаляет запись ajax-запросом и перерисовывает
        # таблицу тем же POST …/search; на больших справочниках («Категории», 500+
        # записей) перерисовка дольше 10 с wait_hidden — ждём сам ответ /search.
        with self.page.expect_response(self._is_table_search, timeout=30000):
            confirm_button.click()
        self.wait_hidden(row)
