from playwright.sync_api import Page
from utils.logger import logger


class TestPage:
    """Page Object для прохождения теста."""

    def __init__(self, page: Page):
        self.page = page

    def start_test(self):
        """Открыть индивидуальное обучение."""
        try:
            for _ in range(15):
                btn = self.page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    self.page.wait_for_timeout(300)
                else:
                    break
        except:
            pass

        self.page.locator("text=Индивидуальное обучение").first.click(force=True)
        self.page.wait_for_timeout(2000)
        logger.info("Индивидуальное обучение открыто")

    def open_activity_by_name(self, name: str):
        """Найти и открыть активность по имени."""
        self.page.locator(f"text={name}").first.click(force=True)
        self.page.wait_for_timeout(2000)
        logger.info(f"Активность '{name}' открыта")

    def click_start(self):
        """Нажать 'Начать'."""
        self.page.locator("span:has-text('Начать')").first.click(force=True)
        self.page.wait_for_timeout(3000)
        logger.info("Тест запущен")

    def answer_question(self, answer_index: int = 0):
        """Ответить на вопрос (выбрать ответ по индексу)."""
        answers = self.page.locator('.answer-item, [data-qa="answer"]')
        if answers.count() > answer_index:
            answers.nth(answer_index).click(force=True)
            self.page.wait_for_timeout(500)
            logger.info(f"Выбран ответ #{answer_index}")

    def click_next(self):
        """Нажать 'Далее'."""
        self.page.locator("button:has-text('Далее'), span:has-text('Далее')").first.click(force=True)
        self.page.wait_for_timeout(1000)
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