from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class LpdPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def start_lpd(self):
        """Открыть LPD через индивидуальное обучение."""
        self.click("text=Индивидуальное обучение")
        self.page.wait_for_timeout(1000)
        self.complete_program_onboarding()
        self.click("text=ЛПД")
        self.page.wait_for_timeout(1000)
        self.complete_program_onboarding()
        # Клик по первому LPD в списке
        self.page.locator("span:has-text('ЛПД'), .lpd-item, .content-item").first.click()
        self.page.wait_for_timeout(1000)
        self.page.locator("span:has-text('Начать')").first.click()

    def start_stream_lpd(self, program_name: str):
        """Открыть LPD через программу (поток)."""
        self.page.locator(f"span:has-text('{program_name}')").first.click()
        self.page.wait_for_timeout(2000)
        self.page.screenshot(path="allure-results/lpd_stream_inside.png")
        self.complete_program_onboarding()


    def complete_program_onboarding(self):
        """Пройти онбординг."""
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