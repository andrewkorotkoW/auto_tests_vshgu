from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class TestPage(BasePage):
    """Page Object для прохождения теста."""

    def __init__(self, page: Page):
        super().__init__(page)

    def start_test(self):
        """Открыть индивидуальное обучение."""
        try:
            for _ in range(15):
                btn = self.page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                else:
                    break
        except:
            pass

        self.click_and_wait(self.page.locator("text=Индивидуальное обучение").first, force=True)
        logger.info("Индивидуальное обучение открыто")

    def open_activity_by_name(self, name: str):
        """Найти и открыть активность по имени."""
        self.click_and_wait(self.page.locator(f"text={name}").first, force=True)
        logger.info(f"Активность '{name}' открыта")

    def click_start(self):
        """Нажать 'Начать'."""
        self.click_and_wait(self.page.locator("span:has-text('Начать')").first, force=True)
        logger.info("Тест запущен")

    def answer_question(self, answer_index: int = 0):
        """Ответить на вопрос (выбрать ответ по индексу)."""
        answers = self.page.locator('.answer-item, [data-qa="answer"]')
        if answers.count() > answer_index:
            answers.nth(answer_index).click(force=True)
            self.wait_loaded()
            logger.info(f"Выбран ответ #{answer_index}")

    def click_next(self):
        """Нажать 'Далее'."""
        self.click_and_wait(
            self.page.locator("button:has-text('Далее'), span:has-text('Далее')").first, force=True
        )
        logger.info("Кнопка 'Далее' нажата")

    def complete_test(self):
        """Пройти тест до конца."""
        for i in range(10):
            try:
                self.answer_question(0)
                self.click_next()
            except:
                logger.info(f"Тест завершён после {i} вопросов")
                break
