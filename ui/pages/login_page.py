from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from config.settings import settings
from utils.logger import logger


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def login(self, email: str, password: str):
        self.page.goto(f"{settings.UI_BASE_URL}/auth/main")
        self.wait_for('input[name="email_or_login"]')
        self.fill('input[name="email_or_login"]', email)
        self.fill('input[name="password"]', password)

        self.click('button:has-text("Войти")')
        self.page.wait_for_load_state("networkidle")
        self.handle_modal()
        self.complete_training()

    def handle_modal(self):
        """Обработать модальное окно после логина."""
        try:
            self.page.wait_for_selector(".v-overlay, .v-dialog, [class*=modal]", timeout=3000)
            if self.page.locator('input[type="checkbox"]').is_visible(timeout=1000):
                self.page.locator('input[type="checkbox"]').check()
            if self.page.locator("text=Отправить").is_visible(timeout=1000):
                self.click("text=Отправить")
            logger.info("✅ Модальное окно обработано")
        except:
            logger.info("Модальное окно не появилось")

    def complete_training(self):  # ← переименовано
        try:
            self.page.wait_for_timeout(1500)
            start_btn = self.page.locator("span.v-btn__content:has-text('Пройти обучение')")
            if start_btn.is_visible(timeout=3000):
                start_btn.click()
                self.page.wait_for_timeout(500)
                logger.info("✅ Нажали 'Пройти обучение'")
            while self.page.locator("text=Далее").is_visible(timeout=2000):
                self.click("text=Далее")
                self.page.wait_for_timeout(300)
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
                self.page.wait_for_timeout(500)
            logger.info("✅ Обучение завершено")
        except Exception as e:
            logger.info(f"Обучение не появилось: {e}")

    def logout(self):
        """Выйти из системы."""
        # Клик по аватарке — первая v-btn в хедере
        self.page.locator("header .v-btn").first.click()
        self.page.wait_for_timeout(500)
        # Клик по "Выйти"
        self.page.locator("svg[icon='logout']").first.click()
        self.page.wait_for_timeout(1000)
