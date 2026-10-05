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
search здесь не проверяет результат, это должен делать вызывающий тест."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage


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
