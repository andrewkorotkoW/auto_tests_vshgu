from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class AdminPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def go_to_admin(self):
        """Перейти в Админку из меню пользователя."""
        admin_item = self.page.locator("div.v-list-item-title:has-text('Админка')").first
        self.click_and_wait(self.page.locator("[data-onboarding-step='user-menu']").first, wait_for=admin_item, force=True)
        self.click_and_wait(admin_item, force=True)

    def open_activity_base(self):
        """Открыть Базу Активити."""
        self.click_and_wait(self.page.locator("div.v-list-item__title:has-text('База Активити')").first, force=True)

    def search_activity(self, name: str):
        """Поиск активити по названию."""
        self.page.locator('[data-qa="km-search"]').fill(name)
        self.wait_loaded()

    def click_activity(self, name: str):
        """Кликнуть по активити в списке."""
        self.click_and_wait(self.page.locator(f"text={name}").first, force=True)

    def check_activity_status(self):
        """Проверить, что активити активна (зелёная кнопка mdi-check)."""
        btn = self.page.locator("button.button-admin i.mdi-check")
        assert btn.is_visible(timeout=5000), "Активити не активна!"
        logger.info("Статус: Активен (зелёная кнопка mdi-check)")