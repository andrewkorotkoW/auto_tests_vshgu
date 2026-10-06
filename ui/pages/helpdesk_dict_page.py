"""Админка хелпдеска → справочники (7 шт. с одинаковым паттерном: /admin/dict/category,
/admin/tag, /admin/dict/applicant_type, /admin/dict/request_source, /admin/dict/request_type,
/admin/dict/processing_result, /admin/blacklist — см. docs/helpdesk_recon.md §3). Один
параметризуемый page-объект вместо 7 копий: список/создание/удаление переиспользуют
HelpdeskAdminPage.table/row/delete_row/open_create_form/submit_form, поле формы (`value_field`)
и путь (`PATH`) задаются в конструкторе — как у api.endpoints.helpdesk.HelpdeskDictEndpoint.

У шести справочников поле называется «Значение» (реальный name-атрибут — `value`, кроме тега —
там `name`) + обязательный select2 «Системная группа» (`group_id`, подтверждено живым прогоном:
без него сервер отвечает 422, хотя разведка по вёрстке посчитала поле необязательным). У
«Чёрного списка адресов» вместо «Значение» — поле «Почтовый адрес» (`email`), без группы."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage


class HelpdeskDictPage(HelpdeskAdminPage):
    def __init__(self, page, path: str, value_field: str, has_group: bool = True):
        super().__init__(page)
        self.PATH = path
        self.value_field = value_field
        self.has_group = has_group

    def fill_create_form(self, value: str, group_name: str = None) -> None:
        self.field(self.value_field).fill(value)
        if group_name and self.has_group:
            combobox = self.page.locator('[bp-field-name="group_id"] [role=combobox]').first
            combobox.click()
            option = self.page.get_by_role("option", name=group_name)
            expect(option).to_be_visible(timeout=10000)
            option.click()

    def create(self, value: str, group_name: str = None) -> None:
        """Полный цикл: открыть форму «Добавить N», заполнить, сохранить, дождаться
        записи в списке."""
        self.open_create_form()
        self.fill_create_form(value, group_name)
        self.submit_form()
        expect(self.row(value)).to_be_visible(timeout=15000)

    def delete(self, value: str) -> None:
        self.delete_row(value)
