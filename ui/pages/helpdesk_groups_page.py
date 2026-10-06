"""Админка хелпдеска → «Группы» (/admin/group, docs/helpdesk_recon.md, кейсы
9510-9514): список системных + Автотест_* групп, создание/редактирование/
просмотр/удаление через форму.

НЕ использовать create/delete на существующих системных группах и их
IMAP/SMTP-настройках — только на своих Автотест_* (см.
api.helpers.data_generator.generate_helpdesk_group_payload). Поля формы
заполняются по `bp-field-name` (HelpdeskAdminPage.field) — реальные
name-атрибуты полей (подтверждено Playwright на develop) отличаются от
логических ключей payload: `prefix` -> `ticket_prefix`, `imap_password` ->
`password` (см. тот же перевод в api.endpoints.helpdesk.HelpdeskEndpoint)."""
from playwright.sync_api import expect

from ui.pages.helpdesk_base_page import HelpdeskAdminPage


class HelpdeskGroupsPage(HelpdeskAdminPage):
    PATH = "/admin/group"

    def fill_create_form(self, payload: dict) -> None:
        """payload — как из generate_helpdesk_group_payload(): name/prefix/email/
        imap_password/imap_host/imap_port/smtp_host/smtp_port (+ опционально users)."""
        self.field("name").fill(payload["name"])
        self.field("ticket_prefix").fill(payload["prefix"])
        self.field("email").fill(payload["email"])
        self.field("password").fill(payload["imap_password"])
        self.field("imap_host").fill(payload["imap_host"])
        self.field("imap_port").fill(str(payload["imap_port"]))
        self.field("smtp_host").fill(payload["smtp_host"])
        self.field("smtp_port").fill(str(payload["smtp_port"]))

    def create_group(self, payload: dict) -> None:
        """Полный цикл: открыть форму «Добавить группу», заполнить, сохранить,
        дождаться созданной группы в списке."""
        self.open_create_form()
        self.fill_create_form(payload)
        self.submit_form()
        expect(self.row(payload["name"])).to_be_visible(timeout=15000)

    def delete_group(self, name: str) -> None:
        """Удалить группу по названию — вызывать только для своих Автотест_*."""
        self.delete_row(name)

    def open_edit_form(self, name: str) -> None:
        row = self.row(name)
        expect(row).to_be_visible(timeout=15000)
        row.locator("[data-button-type='update']").first.click()
        self.wait_loaded()

    def open_show_page(self, name: str) -> None:
        row = self.row(name)
        expect(row).to_be_visible(timeout=15000)
        row.locator("[data-button-type='show']").first.click()
        self.wait_loaded()
