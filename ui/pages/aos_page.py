import re

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

        # Плеер (/testing/player/<id>/<uuid>) рендерится с задержкой: после networkidle
        # ещё ~5-8 с виден только логотип-лоадер, потом «Вступительный слайд» с кнопкой
        # «Начать» (screens.intro.is_active в payload АОС) либо сразу первая группа
        # вопросов. Раньше ждали is_visible(timeout=5000) — у Locator.is_visible таймаут
        # игнорируется (проверка мгновенная), интро ещё не было, и клик пропускался.
        # Сначала — переход в плеер: на странице программы тоже есть «Начать» (та, что
        # только что нажали), и без этого ожидание ловило её, а интро в плеере оставалось
        # некликнутым (тест ждал шкалы 30 с на вступительном слайде).
        self.page.wait_for_url(re.compile(r"/testing/player/"), timeout=self.PLAYER_TIMEOUT)
        self.wait_visible(self.page.locator(f"{self.INTRO_START_BTN}, {self.LIKERT}").first, timeout=self.PLAYER_TIMEOUT)
        # Кнопка интро отрисована раньше, чем плеер навесил обработчик: одиночный клик
        # сразу после появления «проглатывался», и тест ждал шкалы на интро-слайде
        # (скриншот падения 10.11.2026). Поэтому — клик, пауза, и повтор, пока слайд не
        # сменился первой группой вопросов.
        intro_start_btn = self.page.locator(self.INTRO_START_BTN).first
        for _ in range(8):
            if self.page.locator(self.LIKERT).count() > 0:
                break
            if intro_start_btn.count() > 0 and intro_start_btn.is_visible():
                intro_start_btn.click()
            self.page.wait_for_timeout(2500)

    def complete_program_onboarding(self):
        """Пройти онбординг после клика по программе (см. UserSidebarPage.pass_onboarding —
        учитывает затемнение, которое переживает исчезновение кнопки «Далее»)."""
        UserSidebarPage(self.page).pass_onboarding()

    # ------------------------------------------------------------ прохождение анкеты
    # Структура плеера АОС (разведка develop 10.11.2026, АОС из generate_aos_payload —
    # без своих вопросов, анкета по умолчанию): НЕ визард «один вопрос — один экран», а
    # ГРУППЫ вопросов по одной на экран. Группа «Вебинар <преподаватель> «<мероприятие>»»:
    # три шкалы 1–10 (.likert-scale, кнопки .likert-scale__btn), комментарий (textarea),
    # чекбоксы компетенций (.multi-answer__checkbox); группа «Организация учебного дня»:
    # шкалы + комментарий. Единственная кнопка .question-tools__btn_primary: «Ответить»
    # (disabled, пока не отвечены все шкалы) → после ответа становится «Перейти к
    # следующей группе» либо «Завершить» на последней группе → экран «Спасибо за
    # прохождение опроса!» с кнопкой «Завершить» → возврат в «Моё обучение».
    PLAYER_TIMEOUT = 30000
    INTRO_START_BTN = "button:has-text('Начать')"
    LIKERT = ".likert-scale"  # кнопки шкалы внутри — .likert-scale__btn с текстом 1…10
    CHECKBOX = ".multi-answer__checkbox input[type='checkbox']"
    TEXTAREA = ".input-word-answer textarea"
    PRIMARY_BTN = ".question-tools__btn_primary"
    THANKS_TEXT = "text=Спасибо за прохождение опроса"
    FINISH_BTN = "button:has-text('Завершить')"

    def wait_group_loaded(self):
        """Дождаться группы вопросов (первой шкалы) — плеер рисует её с задержкой."""
        self.wait_visible(self.page.locator(self.LIKERT).first, timeout=self.PLAYER_TIMEOUT)

    def answer_group(self, score: int = 10, comment: str = "Автотест", checkboxes: int = 3) -> dict:
        """Ответить на всё в текущей группе: каждая шкала — кнопка `score`, каждое текстовое
        поле — `comment`, первые `checkboxes` чекбоксов. Возвращает, сколько чего нашли."""
        scales = self.page.locator(self.LIKERT)
        for i in range(scales.count()):
            # get_by_role(exact=True): has_text="1" совпал бы и с «10»
            scales.nth(i).get_by_role("button", name=str(score), exact=True).click()
        areas = self.page.locator(self.TEXTAREA)
        for i in range(areas.count()):
            areas.nth(i).fill(comment)
        boxes = self.page.locator(self.CHECKBOX)
        checked = min(checkboxes, boxes.count())
        for i in range(checked):
            boxes.nth(i).check(force=True)
        return {"scales": scales.count(), "textareas": areas.count(), "checkboxes": checked}

    def submit_group(self) -> str:
        """Нажать «Ответить» и дождаться, пока та же кнопка сменит подпись на «Перейти к
        следующей группе» / «Завершить»; нажать её. Возвращает эту подпись."""
        btn = self.page.locator(self.PRIMARY_BTN)
        expect(btn).to_have_text("Ответить", timeout=self.PLAYER_TIMEOUT)
        expect(btn).to_be_enabled(timeout=self.PLAYER_TIMEOUT)
        btn.click()
        expect(btn).not_to_have_text("Ответить", timeout=self.PLAYER_TIMEOUT)
        label = btn.inner_text().strip()
        btn.click()
        return label

    def complete_questionnaire(self, max_groups: int = 10) -> int:
        """Пройти все группы до экрана «Спасибо за прохождение опроса!» и нажать на нём
        «Завершить» (плеер возвращает в «Моё обучение»). Возвращает число групп."""
        groups = 0
        for groups in range(1, max_groups + 1):
            self.wait_group_loaded()
            answered = self.answer_group()
            label = self.submit_group()
            logger.info(f"АОС: группа {groups} отвечена ({answered}) → «{label}»")
            if label.startswith("Завершить"):
                break
        else:
            raise AssertionError(f"Анкета не дошла до «Завершить» за {max_groups} групп")
        expect(self.page.locator(self.THANKS_TEXT)).to_be_visible(timeout=self.PLAYER_TIMEOUT)
        self.click_and_wait(self.page.locator(self.FINISH_BTN).first, force=True)
        return groups

    def launch_questionnaire(self):
        """Запустить анкету, если программа уже открыта (или мы на странице плеера)."""
        start_btn = self.page.locator("span:has-text('Начать')").first
        self.click_and_wait(start_btn, force=True)
