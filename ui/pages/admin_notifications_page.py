"""Админка → «Уведомления» (/admin/notifications): вкладка «Все уведомления» (?i=3)
и локатор строки таблицы с созданным уведомлением.

Структура проверена вручную через Playwright на --env develop (HEADLESS=1): таблица —
.v-data-table.vs-table, первая колонка «Название» содержит название/заголовок
уведомления (проверено на реальной строке из таблицы).

Известный нюанс (кандидат в дефекты, см. README «Уведомления и техподдержка»): строки
отсортированы по «Дата отправки», а не по дате создания. Уведомление, созданное через
POST /notifications/create с send_at=null (как отдаёт NotificationsEndpoint.create по
умолчанию), не появилось в таблице ни на первой странице, ни после ~15 c ожидания и
перезагрузки — судя по всему, попадает в таблицу только после фактической отправки.
Тесту может понадобиться дождаться отправки (или найти другой способ её вызвать)
до проверки notification_row()."""
from playwright.sync_api import Page, Locator
from ui.pages.base_page import BasePage


class AdminNotificationsPage(BasePage):
    ALL_PATH = "/admin/notifications?i=3"

    def __init__(self, page: Page):
        super().__init__(page)

    def open_all(self, ui_base_url: str) -> None:
        """Открыть вкладку «Все уведомления»."""
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.ALL_PATH}")
        self.wait_loaded()

    @property
    def table(self) -> Locator:
        return self.page.locator(".v-data-table.vs-table").first

    def notification_row(self, name: str) -> Locator:
        """Строка таблицы по названию/заголовку уведомления (колонка «Название»).
        Строка может оказаться на любой из нескольких десятков страниц пагинации —
        метод не листает страницы сам, это на усмотрение теста (или отдать name через
        фильтр «Получатели»/«Отправители» в диалоге «Фильтр», если понадобится)."""
        return self.page.locator(f"xpath=//table//tr[td[1][contains(., '{name}')]]").first
