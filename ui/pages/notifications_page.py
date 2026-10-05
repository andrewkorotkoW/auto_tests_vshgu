"""Пользовательская страница «Уведомления» (/portal-notifications): список уведомлений
пользователя, тема/текст конкретного уведомления, открытие уведомления.

Структура проверена вручную через Playwright на --env develop (HEADLESS=1): карточка —
.portal-notification, тема — .portal-notification__title, текст — .portal-notification__text.
Оба поля уже полностью видны в карточке без разворачивания — open_notification() кликает
по карточке (в перехваченных запросах при клике не было отдельного вызова "прочитано",
но кнопка-стрелка в карточке на это похожа, поэтому клик всё равно оставлен как «открытие»)."""
from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class NotificationsPage(BasePage):
    PATH = "/portal-notifications"

    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = UserSidebarPage(page)

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PATH}")
        self.wait_loaded()
        self.sidebar.dismiss_popups()

    @property
    def notifications_list(self) -> Locator:
        return self.page.locator(".portal-notifications__content")

    def notification_titles(self) -> list:
        """Темы всех уведомлений, видимых в списке пользователя."""
        return [t.strip() for t in self.notifications_list.locator(".portal-notification__title").all_inner_texts()]

    def notification_card(self, title: str) -> Locator:
        """Карточка уведомления по теме (title)."""
        return self.page.locator(f".portal-notification:has-text('{title}')").first

    def notification_text(self, title: str) -> str:
        """Текст уведомления с заданной темой."""
        return self.notification_card(title).locator(".portal-notification__text").inner_text().strip()

    def open_notification(self, title: str) -> None:
        """Кликнуть по уведомлению с заданной темой."""
        card = self.notification_card(title)
        expect(card).to_be_visible(timeout=15000)
        card.click(force=True)
