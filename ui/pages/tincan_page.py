from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


class TincanPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def _click_program_card(self, program_name: str):
        """Открыть карточку программы в «Моё обучение». Заголовок текстовый, переход —
        отдельной кнопкой «Перейти к программе» внутри карточки (см. AosPage)."""
        card_title = self.page.locator(f"text={program_name}").first
        expect(card_title).to_be_visible(timeout=15000)
        goto_btn = self.page.locator("button:has-text('Перейти к программе'), a:has-text('Перейти к программе')").first
        if goto_btn.count() > 0:
            self.click_and_wait(goto_btn, force=True)
        else:
            self.click_and_wait(card_title, force=True)

    def start_tincan(self, program_name: str):
        self._click_program_card(program_name)
        self.complete_program_onboarding()

        # ===== ПРОВЕРКИ (до Начать) =====
        title = self.page.locator("div.activity-card__title, div.details__title").first.text_content()
        assert "_внешка" in title, f"Название не совпадает: {title}"
        logger.info(f"Название: {title}")

        date_span = self.page.locator("span:has-text('—')").first.text_content()
        assert "2026" in date_span, f"Даты не совпадают: {date_span}"
        logger.info(f"Даты: {date_span}")

        sub_file = self.page.locator("span.files-table__text:has-text('sub_files')")
        assert sub_file.is_visible(timeout=3000), "Доп. файл не отображается!"
        logger.info("Доп. файлы отображаются")
        # ============================

        with self.page.context.expect_page() as new_page_info:
            self.page.locator("span:has-text('Начать')").first.click(force=True)
        course_page = new_page_info.value
        course_page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

        self.frame = course_page.frame_locator("#iframe")
        learn_btn = self.wait_visible(self.frame.locator("button:has-text('Перейти к изучению')").first)
        learn_btn.click(force=True)
        start_test_btn = self.wait_visible(self.frame.locator("button:has-text('Начать тест')").first)
        start_test_btn.click(force=True)
        course_page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

        self.page = course_page

    def complete_program_onboarding(self):
        """См. UserSidebarPage.pass_onboarding — учитывает затемнение, которое переживает
        исчезновение кнопки «Далее»."""
        UserSidebarPage(self.page).pass_onboarding()

    def answer_first_radio(self):
        """Выбрать первый radio-ответ."""
        self.click_and_wait(self.page.locator("label.c-radio").first)

    def answer_nth_option(self, n: int = 3):  # ← ДОБАВИТЬ ЭТОТ МЕТОД
        """Выбрать n-й radio-ответ."""
        self.frame.locator(f"label.c-radio:nth-child({n})").first.click(force=True)

    def click_answer(self):
        """Нажать Ответить."""
        self.click_and_wait(self.page.locator("span.c-button__slot:has-text('Ответить')"))

    def click_next_arrow(self):
        """Нажать стрелку Далее (SVG)."""
        arrow = self.page.locator(".navigation-button-item__arrow svg").first
        if arrow.is_visible(timeout=2000):
            self.click_and_wait(arrow)

    def open_program(self, program_name: str):
        """Открыть программу и проверить данные курса."""
        self._click_program_card(program_name)
        self.complete_program_onboarding()
        return self.page

    def start_tincan_individual(self):
        """Открыть курс через инд. обучение."""
        individual_education = self.page.locator("text=Индивидуальное обучение").first
        expect(individual_education).to_be_visible(timeout=settings.UI_TIMEOUT)
        individual_education.click(force=True)
        self.complete_program_onboarding()
        UserSidebarPage(self.page).dismiss_popups()
        course_card = self.page.locator("span:has-text('Tincan'), span:has-text('Автотест')").first
        expect(course_card).to_be_visible(timeout=30000)
        course_card.click(force=True)
        self.complete_program_onboarding()

        # Проверки
        title = self.page.locator("div.activity-card__title, div.details__title").first.text_content()
        assert "_внешка" in title, f"Название не совпадает: {title}"
        date_span = self.page.locator("span:has-text('—')").first.text_content()
        assert "2026" in date_span, f"Даты не совпадают: {date_span}"
        sub_file = self.page.locator("span.files-table__text:has-text('sub_files')")
        assert sub_file.is_visible(timeout=3000), "Доп. файл не отображается!"

        # Открыть курс (без новой вкладки)
        self.page.locator("button.v-btn:has-text('Начать')").first.evaluate("el => el.click()")

        self.frame = self.page.frame_locator("#iframe")
        learn_btn = self.wait_visible(self.frame.locator("button:has-text('Перейти к изучению')").first)
        learn_btn.click(force=True)
        start_test_btn = self.wait_visible(self.frame.locator("button:has-text('Начать тест')").first)
        start_test_btn.click(force=True)

    def answer_by_text(self, text: str):
        """Выбрать ответ по тексту."""
        self.frame.locator(f"div.choice-answer__text:has-text('{text}')").first.click(force=True)




