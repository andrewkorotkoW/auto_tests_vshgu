from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from config.settings import settings
from utils.logger import logger


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def login(self, email: str, password: str, base_url: str = None, handle_onboarding: bool = True):
        self.page.goto(f"{base_url or settings.UI_BASE_URL}/auth/main")
        self.wait_for('input[name="email_or_login"]')
        self.fill('input[name="email_or_login"]', email)
        self.fill('input[name="password"]', password)

        self.click('button:has-text("Войти")')
        self.page.wait_for_load_state("networkidle")
        if handle_onboarding:
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
            start_btn = self.page.locator("span.v-btn__content:has-text('Пройти обучение')")
            if start_btn.is_visible(timeout=3000):
                start_btn.click()
                logger.info("✅ Нажали 'Пройти обучение'")
            while self.page.locator("text=Далее").is_visible(timeout=2000):
                self.click("text=Далее")
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
                self.wait_loaded()
            logger.info("✅ Обучение завершено")
        except Exception as e:
            logger.info(f"Обучение не появилось: {e}")

    def logout(self):
        """Выйти из системы."""
        # Клик по аватарке — первая v-btn в хедере, ждём появления пункта "Выйти"
        logout_icon = self.page.locator("svg[icon='logout']").first
        self.click_and_wait(self.page.locator("header .v-btn").first, wait_for=logout_icon)
        # Клик по "Выйти"
        self.click_and_wait(logout_icon)
