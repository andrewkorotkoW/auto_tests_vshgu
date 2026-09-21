"""Онбординг: первичное заполнение анкеты (регион/муниципалитет/согласие на ПД),
прохождение «Интерактивного руководства», повторный запуск и закрытие крестиком.

Перенос src/ui/pages/onboarding_page.py и src/ui/locators/onboarding_locators.py
коллеги (репозиторий lms, feature/my-tests). В отличие от источника — без
диагностических wait_for_timeout(10000)/print и без is_visible()-опросов как
основного способа ожидания: состояния (первичный/повторный онбординг) определяются
через один web-first expect() на объединённый локатор (Locator.or_).
"""
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError, expect

REGISTRATION_MODAL = "div.v-dialog:has-text('Пожалуйста, заполните'), div.v-dialog:has-text('обработку персональных данных')"
REGION_AUTOCOMPLETE = "div.v-autocomplete:has(label:has-text('Регион'))"
MUNICIPALITY_AUTOCOMPLETE = "div.v-autocomplete:has(label:has-text('Муниципальное образование'))"
AUTOCOMPLETE_MENU_ICON = "i.v-autocomplete__menu-icon"
AUTOCOMPLETE_OVERLAY = "div.v-overlay__content, div.v-menu__content"
LIST_ITEM_TITLE = "div.v-list-item__title"
CONSENT_CHECKBOX_INPUT = "input[type='checkbox']"
SUBMIT_BUTTON = "button:has-text('Отправить')"

ONBOARDING_MODAL = "div.v-dialog:has-text('Интерактивное руководство')"
START_BUTTON = "button:has-text('Пройти обучение')"
NEXT_BUTTON = "button:has-text('Далее')"
FINISH_BUTTON = "button:has-text('Завершить')"

# Несколько версток одной и той же кнопки на разных страницах — объединяем через
# запятую (CSS list selector = логическое ИЛИ), а не перебором в цикле.
REPEAT_ONBOARDING_BUTTON = ", ".join([
    "i.sidebar-onboarding-restart-btn__icon[role='button']",
    "i.sidebar-onboarding-restart-btn__icon",
    ".sidebar-onboarding-restart-btn i.sidebar-onboarding-restart-btn__icon",
    "div.sidebar-onboarding-restart-btn i",
])
CLOSE_ONBOARDING_BUTTON = ", ".join([
    "[data-qa='onboarding-popup-close']",
    "button[aria-label*='Закрыть' i]",
    "button[aria-label*='Close' i]",
    "button:has(i.mdi-close)",
])


class OnboardingPage:
    def __init__(self, page: Page):
        self.page = page

    # ── Первая модалка: анкета первичной регистрации ────────────────────

    @property
    def registration_modal(self) -> Locator:
        return self.page.locator(REGISTRATION_MODAL)

    def wait_for_registration_modal(self, timeout: int = 15000) -> None:
        expect(self.registration_modal).to_be_visible(timeout=timeout)

    def _select_first_autocomplete_option(self, field_selector: str) -> None:
        field = self.page.locator(field_selector)
        if not field.is_visible(timeout=8000):
            return

        arrow = field.locator(AUTOCOMPLETE_MENU_ICON).first
        expect(arrow).to_be_visible(timeout=5000)
        arrow.click(timeout=5000)

        overlay = self.page.locator(AUTOCOMPLETE_OVERLAY)
        expect(overlay).to_be_visible(timeout=15000)

        options = self.page.locator(LIST_ITEM_TITLE)
        expect(options.first).to_be_visible(timeout=25000)
        options.first.click(timeout=5000)

        expect(overlay).to_be_hidden(timeout=12000)

    def accept_consent(self) -> None:
        checkbox = self.registration_modal.locator(CONSENT_CHECKBOX_INPUT).first
        expect(checkbox).to_be_attached(timeout=8000)
        if not checkbox.is_checked():
            checkbox.check(timeout=5000)
        expect(checkbox).to_be_checked(timeout=8000)

    def submit_registration_form(self) -> None:
        submit = self.page.locator(SUBMIT_BUTTON)
        expect(submit).to_be_visible(timeout=15000)
        expect(submit).to_be_enabled(timeout=30000)
        submit.click(timeout=10000)

    def fill_registration_form(self) -> None:
        """Заполняет анкету первичной регистрации: регион, муниципалитет (первый
        доступный вариант в каждом автокомплите), согласие на ПД, отправка."""
        self._select_first_autocomplete_option(REGION_AUTOCOMPLETE)
        self._select_first_autocomplete_option(MUNICIPALITY_AUTOCOMPLETE)
        self.accept_consent()
        self.submit_registration_form()

    # ── Вторая модалка: «Интерактивное руководство» ──────────────────────

    @property
    def onboarding_modal(self) -> Locator:
        return self.page.locator(ONBOARDING_MODAL)

    @property
    def repeat_onboarding_button(self) -> Locator:
        return self.page.locator(REPEAT_ONBOARDING_BUTTON).first

    @property
    def close_onboarding_button(self) -> Locator:
        return self.page.locator(CLOSE_ONBOARDING_BUTTON).first

    def wait_for_primary_onboarding_or_repeat(self, timeout: int = 15000) -> str:
        """Ждёт один web-first вызов на объединённый локатор (модалка ИЛИ кнопка
        «Далее» ИЛИ кнопка повторного онбординга) и определяет итоговое состояние:
        "primary" — показан первичный онбординг, "repeat" — пользователь уже прошёл
        его раньше (виден только значок перезапуска), "timeout" — не появилось ничего."""
        next_button = self.page.locator(NEXT_BUTTON)
        combined = self.onboarding_modal.or_(next_button).or_(self.repeat_onboarding_button)
        try:
            combined.first.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return "timeout"

        if self.onboarding_modal.is_visible(timeout=500) or next_button.is_visible(timeout=500):
            return "primary"
        return "repeat"

    def start_onboarding_if_present(self, timeout: int = 3000) -> bool:
        start_button = self.page.locator(START_BUTTON)
        if start_button.is_visible(timeout=timeout):
            start_button.click(timeout=5000)
            return True
        return False

    def complete_onboarding(self, max_steps: int = 20) -> None:
        """Проходит все слайды кликами «Далее» и завершает «Завершить»."""
        next_button = self.page.locator(NEXT_BUTTON)
        finish_button = self.page.locator(FINISH_BUTTON)

        for _ in range(max_steps):
            if finish_button.is_visible(timeout=2000):
                break
            expect(next_button).to_be_visible(timeout=10000)
            next_button.click(timeout=5000)
        else:
            raise AssertionError(f"Онбординг не завершился после {max_steps} слайдов")

        expect(finish_button).to_be_visible(timeout=5000)
        finish_button.click(timeout=5000)
        expect(self.onboarding_modal).not_to_be_visible(timeout=15000)

    # ── Повторный онбординг: перезапуск и закрытие крестиком ────────────

    def restart_onboarding(self) -> None:
        expect(self.repeat_onboarding_button).to_be_visible(timeout=10000)
        # force=True: значок перезапуска — маленькая иконка в сайдбаре, иногда на доли
        # секунды перекрыта соседней анимацией меню
        self.repeat_onboarding_button.click(timeout=5000, force=True)

    def close_onboarding(self) -> None:
        expect(self.close_onboarding_button).to_be_visible(timeout=10000)
        self.close_onboarding_button.click(timeout=5000, force=True)
        expect(self.page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)
        expect(self.onboarding_modal).not_to_be_visible(timeout=10000)
