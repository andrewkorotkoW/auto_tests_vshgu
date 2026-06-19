from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class AosPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_program(self, program_name: str):
        """Открыть программу без запуска АОС."""
        self.page.locator(f"span:has-text('{program_name}')").first.click()
        self.page.wait_for_timeout(1000)
        self.complete_program_onboarding()

    def start_aos(self, program_name: str):
        # Открываем программу
        self.page.locator(f"span:has-text('{program_name}')").first.click()
        self.page.wait_for_timeout(1000)
        self.complete_program_onboarding()

        # Кликаем по вкладке «Анкета обратной связи»
        self.page.locator("span:has-text('Анкета обратной связи')").first.click()
        self.page.wait_for_timeout(2000)

        # Запускаем анкету
        self.page.locator("span:has-text('Начать')").first.click()
        self.page.wait_for_timeout(1000)
        self.page.locator("span:has-text('Начать')").first.click()

    def complete_program_onboarding(self):
        """Пройти онбординг после клика по программе."""
        try:
            self.page.wait_for_timeout(3000)
            for _ in range(25):
                btn = self.page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=3000):
                    btn.click(force=True)
                    self.page.wait_for_timeout(500)
                else:
                    break
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
                self.page.wait_for_timeout(500)
            logger.info("✅ Онбординг программы пройден")
        except Exception as e:
            logger.info(f"Онбординг программы: {e}")

    def answer_first_option(self):
        """Выбрать первый вариант ответа."""
        self.page.wait_for_timeout(500)
        # label
        label = self.page.locator("label").first
        if label.count() > 0:
            label.click(force=True)
            return
        # v-radio
        radio = self.page.locator(".v-radio").first
        if radio.count() > 0:
            radio.click(force=True)
            return

    def answer_first_checkboxes(self, count: int = 3):
        """Выбрать первые N чекбоксов."""
        checkboxes = self.page.locator("input[type='checkbox']")
        for i in range(min(count, checkboxes.count())):
            checkboxes.nth(i).check()

    def answer_textarea(self, text: str):
        self.page.locator("textarea.v-field__input").fill(text)

    def click_answer(self):
        self.page.locator("text=Ответить").click(force=True)

    def click_next(self):
        self.click("text=Вперед")

    def click_finish(self):
        """Нажать Завершить в конце АОС."""
        self.page.wait_for_timeout(1000)
        # Пробуем найти кнопку «Завершить» и кликнуть
        finish_btn = self.page.locator("button:has-text('Завершить')").first
        if finish_btn.is_visible(timeout=5000):
            finish_btn.click(force=True)
            self.page.wait_for_timeout(1000)
        # Если есть второе окно подтверждения — ещё раз
        confirm_btn = self.page.locator("button:has-text('Завершить')").first
        if confirm_btn.is_visible(timeout=3000):
            confirm_btn.click(force=True)
            self.page.wait_for_timeout(1000)

    def launch_questionnaire(self):
        """Запустить анкету, если программа уже открыта (или мы на странице плеера)."""
        self.page.locator("span:has-text('Начать')").first.click()
        self.page.wait_for_timeout(1000)
        self.page.locator("span:has-text('Начать')").first.click()