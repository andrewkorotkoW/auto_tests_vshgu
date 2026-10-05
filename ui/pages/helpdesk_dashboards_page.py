"""Админка хелпдеска → «Дашборды» (/admin/dashboard, docs/helpdesk_recon.md,
кейс 9625): графики Highcharts, каждый подгружается отдельным
`POST /admin/dashboard/data/<metric>`. Блок ХелпРанепа (2 метрики) и доп.
метрика «Принято ответов от ИИ» (%), не описанная в выгрузке Test IT v.2.

Не наследует HelpdeskAdminPage — здесь нет списка/CRUD-таблицы, только набор
виджетов и фильтры/интервал/детализация, поэтому локаторы свои."""
from ui.pages.base_page import BasePage


class HelpdeskDashboardsPage(BasePage):
    PATH = "/admin/dashboard"

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}")
        self.wait_loaded()

    def open_filters(self) -> None:
        self.page.get_by_role("button", name="Фильтры").click()

    def set_interval(self, label: str) -> None:
        """label — один из «День»/«Неделя»/«Месяц»/«Год»."""
        self.page.get_by_role("button", name=label, exact=True).click()
        self.wait_loaded()

    def chart_titles(self) -> list:
        """Заголовки всех виджетов-графиков, отрисованных на странице сейчас."""
        return self.page.locator(".highcharts-title").all_inner_texts()
