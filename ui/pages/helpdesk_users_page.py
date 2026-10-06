"""Админка хелпдеска → «Пользователи» (/admin/user, docs/helpdesk_recon.md,
кейсы 9590-9593/9598/9605): список, карточка пользователя, назначение ролей.

Назначение роли — отдельный суб-паттерн: шестерёнка в столбце «Действия» списка
открывает iframe-модалку (`data-tbx-component="CommonIframeModalButton"`) на
`/admin/user/{id}/assign-role` с чекбоксами ровно «Администратор»/«Поддержка»/
«Администратор группы» и кнопкой «Сохранить» — работать нужно внутри
`page.frame_locator(...)`, а не в основном документе. На самой карточке
пользователя (/admin/user/{id}/show) иконки назначения ролей больше нет (кейс
9593 устарел) — только редактирование (настройки таблицы тикетов, карандаш).

Поиск по ФИО одним словом не фильтрует список (нужно ≥2 слов), а многословный
поиск пользователя может привести к HTTP 500 на бэкенде (см. recon §5) — метод
search здесь не проверяет результат, это должен делать вызывающий тест.

«Настройки таблицы тикетов» (/admin/user/{id}/edit) — repeatable-поле `settings`:
каждая выбранная колонка — отдельная строка `.repeatable-element` с `<select
name="settings[N][id]">` (опции — id/identity_id/title/content/status/created_at/
updated_at/group_id/user_id/tag/response) и скрытым `settings[N][key]=
ticket_visible_columns`. get_ticket_table_columns/set_ticket_table_columns
читают/переписывают список строк — подтверждено живым прогоном (round-trip
set -> submit -> reload -> get даёт тот же список)."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage

_SETTINGS_HOLDER = "[data-repeatable-holder='settings']"


class HelpdeskUsersPage(HelpdeskAdminPage):
    PATH = "/admin/user"

    def search(self, query: str) -> None:
        """Живой поиск DataTables — отправляется AJAX-ом по мере набора."""
        search_box = self.page.locator("#crudTable_filter input[type=search]")
        search_box.fill("")
        search_box.fill(query)
        self.wait_loaded()

    def open_assign_role_modal(self, user_id: int) -> None:
        """Открыть iframe-модалку назначения ролей для пользователя по его ID
        (строка ищется по email/ФИО в UI — метод принимает готовый ID, чтобы не
        дублировать поиск/парсинг строки здесь)."""
        row = self.row(str(user_id))
        expect(row).to_be_visible(timeout=15000)
        row.locator("[data-tbx-component='CommonIframeModalButton']").first.click()
        self.wait_visible(self.page.frame_locator("iframe").locator("form"))

    def assign_roles(self, admin: bool = False, support: bool = False, group_admin: bool = False) -> None:
        """Отметить чекбоксы ролей внутри уже открытой iframe-модалки
        (open_assign_role_modal) и сохранить."""
        frame = self.page.frame_locator("iframe")
        checkboxes = {
            "Администратор": admin,
            "Поддержка": support,
            "Администратор группы": group_admin,
        }
        for label, checked in checkboxes.items():
            checkbox = frame.get_by_label(label, exact=True)
            if checkbox.is_checked() != checked:
                checkbox.set_checked(checked)
        frame.get_by_role("button", name="Сохранить").click()
        self.wait_loaded()

    def open_show_page(self, ui_base_url: str, user_id: int) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}/{user_id}/show")
        self.wait_loaded()

    def open_edit_form(self, ui_base_url: str, user_id: int) -> None:
        """«Настройки таблицы тикетов» (/admin/user/{id}/edit)."""
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}/{user_id}/edit")
        self.wait_loaded()

    def get_ticket_table_columns(self) -> list:
        """Текущий список выбранных колонок (значения <select>, в порядке строк) —
        вызывать на уже открытой open_edit_form(). Пустой список — колонки по умолчанию,
        настройка ещё не сохранялась."""
        rows = self.page.locator(f"{_SETTINGS_HOLDER} .repeatable-element")
        return [rows.nth(i).locator("select").input_value() for i in range(rows.count())]

    def set_ticket_table_columns(self, columns: list) -> None:
        """Заменить набор колонок на `columns` (значения опций select — id/identity_id/
        title/content/status/created_at/updated_at/group_id/user_id/tag/response) и
        сохранить форму. Вызывать на уже открытой open_edit_form(); для надёжного
        teardown тест должен прочитать исходный список через get_ticket_table_columns()
        до вызова и восстановить его тем же методом в конце (даже при падении теста)."""
        holder = self.page.locator(_SETTINGS_HOLDER)
        while holder.locator(".repeatable-element").count() > 0:
            holder.locator(".repeatable-element .delete-element").first.click()
        for value in columns:
            self.page.locator("button.add-repeatable-element-button").click()
            holder.locator(".repeatable-element").last.locator("select").select_option(value)
        self.submit_form()
