"""Админка хелпдеска → «Тикеты» (/admin/ticket, корень хелпдеска редиректит
сюда, docs/helpdesk_recon.md, кейс 9626) — список обращений с фильтрами,
карточка обращения. Не путать с пользовательской частью тикетов
(/support, ui/pages/tickets_page.py) — она уже покрыта тестами, этот раздел
только для админской навигации/просмотра списка."""
from ui.pages.helpdesk_base_page import HelpdeskAdminPage


class HelpdeskTicketsPage(HelpdeskAdminPage):
    PATH = "/admin/ticket"

    def open_ticket(self, ticket_id: int) -> None:
        row = self.row(str(ticket_id))
        row.locator("[data-button-type='show']").first.click()
        self.wait_loaded()
