"""Админка хелпдеска → «Шаблоны» (/admin/mail-template, заголовок страницы
факт. «Шаблоны ответов», docs/helpdesk_recon.md, кейсы 9620-9624): список,
создание/просмотр/редактирование/удаление шаблона ответа.

Поле «Группа» на форме создания — select2 с множественным выбором; метод
select_groups опционален и используется только если тесту нужно связать
шаблон с конкретной Автотест_* группой.

Поля заполняются по `bp-field-name` (HelpdeskAdminPage.field), а не по
подписи (<label> не связан с полем, как и у групп, см. ui/pages/
helpdesk_groups_page.py). «Содержимое» — WYSIWYG-редактор Quill
(`.ql-editor[contenteditable]`), а не textarea — синхронизирует скрытый
`input[name=content]` при изменении, Playwright `.fill()` поддерживает
contenteditable-элементы напрямую."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage


class HelpdeskTemplatesPage(HelpdeskAdminPage):
    PATH = "/admin/mail-template"

    def fill_create_form(self, payload: dict) -> None:
        """payload — как из generate_helpdesk_template_payload(): name/content/keywords."""
        self.field("name").fill(payload["name"])
        self.page.locator('[bp-field-name="content"] .ql-editor').fill(payload["content"])
        self.field("keywords").fill(payload["keywords"])

    def select_groups(self, group_names: list) -> None:
        """Выбрать группу(ы) в select2-поле «Группа» по названию (опционально)."""
        combobox = self.page.locator('[bp-field-name="groups"] [role=combobox]').first
        for group_name in group_names:
            combobox.click()
            option = self.page.get_by_role("option", name=group_name)
            expect(option).to_be_visible(timeout=10000)
            option.click()

    def create_template(self, payload: dict, group_names: list = None) -> None:
        """Полный цикл: открыть форму «Добавить шаблон ответа», заполнить, сохранить,
        дождаться созданного шаблона в списке."""
        self.open_create_form()
        self.fill_create_form(payload)
        if group_names:
            self.select_groups(group_names)
        self.submit_form()
        expect(self.row(payload["name"])).to_be_visible(timeout=15000)

    def delete_template(self, name: str) -> None:
        self.delete_row(name)

    def open_edit_form(self, name: str) -> None:
        """Реальный маршрут редактирования — {id}/edit (в выгрузке Test IT v.2 кейс
        9623 ошибочно указывал .../create, см. docs/helpdesk_recon.md)."""
        row = self.row(name)
        expect(row).to_be_visible(timeout=15000)
        row.locator("[data-button-type='update']").first.click()
        self.wait_loaded()
