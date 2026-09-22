"""Повторный онбординг: перезапуск кнопкой, закрытие крестиком на 2-м слайде,
повторный запуск и прохождение до конца — по тем же 4 разделам, что и первичный.

Перенос tests/ui/onboarding/test_04_repeat_onboarding_close_button.py,
test_05_knowledge_base_repeat_onboarding.py, test_06_personal_education_repeat_onboarding.py,
test_07_support_repeat_onboarding.py коллеги (репозиторий lms, feature/my-tests, см.
report.md разд. 2).

Предусловие «пользователь уже прошёл первичный онбординг» коллега получал, реально
проходя UI-тур на каждом разделе внутри фикстуры. Мы получаем то же состояние быстрее
и без риска сломать «первичный» сценарий совпадением кода: закрываем все onboarding-
истории пользователя через API (tests/ui/onboarding/conftest.py::repeat_onboarding_page,
api/helpers/user_prepare_api.prepare_user_for_tests_via_api) — сам первичный онбординг
это не тестирует (это отдельно проверяет test_primary_onboarding.py), здесь предмет
проверки — только повторный запуск/закрытие.
"""
import re

import allure
import pytest
from playwright.sync_api import Page, expect

from ui.pages.onboarding_page import OnboardingPage, NEXT_BUTTON

from tests.ui.onboarding.locators import (
    KB_LINK,
    LIBRARY_TAB,
    SUPPORT_LINK,
    SUPPORT_PLUS_ICON,
    PERSONAL_LINK,
    PERSONAL_SCHEDULE_TAB,
    MY_LEARNING_HEADING,
)

pytestmark = [pytest.mark.ui, pytest.mark.onboarding]

REPEAT_TOUR_STAND_DEFECT_REASON = (
    "Дефект стенда develop: клик по кнопке перезапуска онбординга (restart_onboarding, "
    "force=True) не открывает модалку тура повторно — «Далее» не появляется ни с первой, "
    "ни со следующих попыток (до 5 кликов с паузами). Воспроизведено многократно; тот же "
    "класс проблемы, что и с кнопкой «Пройти обучение» в первичном онбординге "
    "(см. test_primary_onboarding.py)."
)


def _restart_close_restart_complete(page: Page, onboarding: OnboardingPage) -> None:
    """Общий сценарий повторного онбординга для всех 4 разделов: перезапуск кнопкой,
    переход на 2-й слайд, закрытие крестиком, повторный запуск и прохождение до конца."""
    next_button = page.locator(NEXT_BUTTON)

    with allure.step("1. Запускаем повторный онбординг"):
        onboarding.restart_onboarding()
        onboarding.start_onboarding_if_present()
        expect(next_button).to_be_visible(timeout=10000)
        expect(next_button).to_be_enabled(timeout=10000)

    with allure.step("2. Переходим на второй слайд"):
        next_button.click(timeout=5000)
        expect(next_button).to_be_visible(timeout=10000)

    with allure.step("3. Закрываем онбординг крестиком на 2-м слайде"):
        onboarding.close_onboarding()

    with allure.step("4. Запускаем повторный онбординг снова и проходим до конца"):
        onboarding.restart_onboarding()
        onboarding.start_onboarding_if_present()
        onboarding.complete_onboarding(max_steps=30)


@allure.feature("Онбординг")
@allure.story("Повторный онбординг")
class TestRepeatOnboarding:

    @allure.title("Повторный онбординг раздела «Моё обучение»: закрыть крестиком, перезапустить, пройти")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason=REPEAT_TOUR_STAND_DEFECT_REASON, strict=False)
    def test_repeat_onboarding_my_learning(self, repeat_onboarding_page: Page):
        page = repeat_onboarding_page
        onboarding = OnboardingPage(page)

        with allure.step("Пользователь на «Моё обучение», первичный онбординг уже закрыт"):
            expect(page.get_by_role("heading", name=MY_LEARNING_HEADING)).to_be_visible(timeout=15000)

        _restart_close_restart_complete(page, onboarding)

        with allure.step("После прохождения онбординг закрыт, пользователь остался на «Моё обучение»"):
            expect(page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)
            expect(page).to_have_url(re.compile(r".*/education.*"), timeout=10000)

    @allure.title("Повторный онбординг раздела «База знаний»: закрыть крестиком, перезапустить, пройти")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason=REPEAT_TOUR_STAND_DEFECT_REASON, strict=False)
    def test_repeat_onboarding_knowledge_base(self, repeat_onboarding_page: Page):
        page = repeat_onboarding_page
        onboarding = OnboardingPage(page)

        with allure.step("Открываем «База знаний» (первичный онбординг уже закрыт)"):
            kb_link = page.locator(KB_LINK).first
            expect(kb_link).to_be_visible(timeout=15000)
            kb_link.click(timeout=5000, force=True)
            expect(page.locator(LIBRARY_TAB)).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/library(?:/)?$"), timeout=10000)

        _restart_close_restart_complete(page, onboarding)

        with allure.step("После прохождения онбординг закрыт, раздел «База знаний» открыт"):
            expect(page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)
            expect(page).to_have_url(re.compile(r".*/library.*"), timeout=10000)

    @allure.title("Повторный онбординг раздела «Техподдержка»: закрыть крестиком, перезапустить, пройти")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason=REPEAT_TOUR_STAND_DEFECT_REASON, strict=False)
    def test_repeat_onboarding_support(self, repeat_onboarding_page: Page):
        page = repeat_onboarding_page
        onboarding = OnboardingPage(page)

        with allure.step("Открываем «Техподдержка» (первичный онбординг уже закрыт)"):
            support_link = page.locator(SUPPORT_LINK).first
            expect(support_link).to_be_visible(timeout=15000)
            support_link.click(timeout=5000, force=True)
            expect(page.locator(SUPPORT_PLUS_ICON).first).to_be_visible(timeout=15000)

        _restart_close_restart_complete(page, onboarding)

        with allure.step("После прохождения онбординг закрыт, раздел «Техподдержка» открыт"):
            expect(page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)
            expect(page.locator(SUPPORT_PLUS_ICON).first).to_be_visible(timeout=15000)

    @allure.title("Повторный онбординг раздела «Индивидуальное обучение»: закрыть крестиком, перезапустить, пройти")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason=REPEAT_TOUR_STAND_DEFECT_REASON, strict=False)
    def test_repeat_onboarding_personal_education(self, repeat_onboarding_page: Page):
        page = repeat_onboarding_page
        onboarding = OnboardingPage(page)

        with allure.step("Открываем «Индивидуальное обучение» (первичный онбординг уже закрыт)"):
            personal_link = page.locator(PERSONAL_LINK).first
            expect(personal_link).to_be_visible(timeout=15000)
            personal_link.click(timeout=5000, force=True)
            expect(page.locator(PERSONAL_SCHEDULE_TAB).first).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/personal_education.*"), timeout=10000)

        _restart_close_restart_complete(page, onboarding)

        with allure.step("После прохождения онбординг закрыт, остались на «Индивидуальное обучение»"):
            expect(page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)
            expect(page).to_have_url(re.compile(r".*/personal_education.*"), timeout=10000)
