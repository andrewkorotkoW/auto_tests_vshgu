from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


class AosPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def _click_program_card(self, program_name: str):
        """Открыть карточку программы в «Моё обучение». Карточка сама по себе не кликабельна —
        заголовок текстовый, переход выполняется кнопкой «Перейти к программе» внутри карточки."""
        card_title = self.page.locator(f"text={program_name}").first
        expect(card_title).to_be_visible(timeout=15000)
        goto_btn = self.page.locator("button:has-text('Перейти к программе'), a:has-text('Перейти к программе')").first
        if goto_btn.count() > 0:
            self.click_and_wait(goto_btn, force=True)
        else:
            self.click_and_wait(card_title, force=True)

    def open_program(self, program_name: str):
        """Открыть программу без запуска АОС."""
        self._click_program_card(program_name)
        self.complete_program_onboarding()

    def start_aos(self, program_name: str):
        # Открываем программу
        self._click_program_card(program_name)
        self.complete_program_onboarding()

        # Тур может показаться заново на странице программы — без повторного вызова
        # затемнение перехватывает клик по вкладке
        UserSidebarPage(self.page).dismiss_popups()

        # Кликаем по вкладке «Анкета обратной связи». Вкладки видны сразу на странице
        # программы (без разворачивания строки модуля), но кликабелен только сам <a>
        # с data-onboarding-step — клик по вложенному <span> с текстом не срабатывает
        # стабильно (перехватывается v-badge разметкой внутри).
        aos_tab = self.page.locator("a[data-onboarding-step='education-tabs-feedback']").first
        self.click_and_wait(aos_tab, force=True)

        # Запускаем анкету
        start_btn = self.page.locator("span:has-text('Начать')").first
        self.click_and_wait(start_btn, force=True)

        # Перед первым вопросом показывается «Вступительный слайд» с отдельной кнопкой «Начать»
        intro_start_btn = self.page.locator("button:has-text('Начать')").first
        if intro_start_btn.is_visible(timeout=5000):
            self.click_and_wait(intro_start_btn, force=True)

    def complete_program_onboarding(self):
        """Пройти онбординг после клика по программе (см. UserSidebarPage.pass_onboarding —
        учитывает затемнение, которое переживает исчезновение кнопки «Далее»)."""
        UserSidebarPage(self.page).pass_onboarding()

    def answer_first_option(self):
        """Выбрать первый вариант ответа."""
        # Селектор матчит много элементов на странице вопроса (все варианты сразу) —
        # wait_visible на нём падает в strict mode, ждём именно первый.
        self.wait_visible(self.page.locator("label, .v-radio").first)
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
        # Пробуем найти кнопку «Завершить» и кликнуть
        finish_btn = self.page.locator("button:has-text('Завершить')").first
        if finish_btn.is_visible(timeout=5000):
            finish_btn.click(force=True)
        # Если есть второе окно подтверждения — ещё раз
        confirm_btn = self.page.locator("button:has-text('Завершить')").first
        if confirm_btn.is_visible(timeout=3000):
            confirm_btn.click(force=True)
            self.wait_loaded()

    def launch_questionnaire(self):
        """Запустить анкету, если программа уже открыта (или мы на странице плеера)."""
        start_btn = self.page.locator("span:has-text('Начать')").first
        self.click_and_wait(start_btn, force=True)
