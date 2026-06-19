from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class ActivityPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def start_external_activity(self, program_name: str):
        """Открыть внешнюю активити (Игровая сессия)."""
        self.page.locator(f"span:has-text('{program_name}')").first.click()
        self.page.wait_for_timeout(1000)
        self.complete_program_onboarding()
        self.page.locator("text=Игровая сессия").first.click()
        self.page.wait_for_timeout(1000)
        self.page.locator("span:has-text('Начать')").first.click()
        self.page.wait_for_timeout(1000)
        self.page.locator("span:has-text('Начать')").first.click()

    def complete_program_onboarding(self):
        try:
            self.page.wait_for_timeout(2000)
            for _ in range(25):
                btn = self.page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    self.page.wait_for_timeout(500)
                else:
                    break
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
            logger.info("Онбординг пройден")
        except Exception as e:
            logger.info(f"Онбординг: {e}")