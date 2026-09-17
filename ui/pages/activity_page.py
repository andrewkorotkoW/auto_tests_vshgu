from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from config.settings import settings
from utils.logger import logger


class ActivityPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def start_external_activity(self, program_name: str):
        """Открыть внешнюю активити (Игровая сессия)."""
        self.click_and_wait(self.page.locator(f"span:has-text('{program_name}')").first)
        self.complete_program_onboarding()
        self.click_and_wait(self.page.locator("text=Игровая сессия").first, wait_for="span:has-text('Начать')")
        self.click_and_wait(self.page.locator("span:has-text('Начать')").first)
        self.page.locator("span:has-text('Начать')").first.click()
        self.wait_loaded()

    def complete_program_onboarding(self):
        """Проходит карусель онбординга, кликая 'Далее' до появления кнопки 'Завершить'."""
        next_btn = self.page.locator('[data-qa="onboarding-popup-next"]')
        finish_btn = self.page.locator("text=Завершить").first
        try:
            for _ in range(25):
                if finish_btn.is_visible():
                    finish_btn.click(force=True)
                    break
                if not next_btn.is_visible(timeout=settings.UI_TIMEOUT):
                    break
                next_btn.click(force=True)
            logger.info("Онбординг пройден")
        except Exception as e:
            logger.info(f"Онбординг: {e}")