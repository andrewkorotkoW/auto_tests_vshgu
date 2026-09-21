from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from utils.logger import logger


class AdminPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def close_tech_banner(self):
        """Закрыть оранжевую плашку «Технические работы», если она появилась после логина."""
        banner = self.page.locator("div.tech-banner")
        if banner.is_visible(timeout=5000):
            close_btn = banner.locator("button").first
            if close_btn.is_visible(timeout=2000):
                close_btn.click(timeout=5000)
            else:
                close_icon = banner.locator(
                    "path[d='M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19"
                    "L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z']"
                ).first
                close_icon.click(timeout=5000)
            expect(banner).not_to_be_visible(timeout=10000)
            logger.info("Закрыли плашку «Технические работы»")

    def go_to_admin(self):
        """Перейти в Админку из меню пользователя."""
        self.close_tech_banner()
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