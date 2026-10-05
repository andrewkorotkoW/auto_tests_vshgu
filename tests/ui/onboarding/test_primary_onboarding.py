"""Первичный онбординг: модалка регион/муниципалитет/согласие на ПД →
«Интерактивное руководство» → по одному тесту на 4 раздела («Моё обучение»,
база знаний/библиотека/избранное, техподдержка, индивидуальное обучение).

Перенос tests/ui/onboarding/test_00_my_learning_page_first_time_onboarding.py,
test_01_knowledge_base_first_time_onboarding.py, test_02_support_page_after_onboarding.py,
test_03_personal_education_first_time_onboarding.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Пользователь — только через нашу фикстуру
created_user (см. tests/ui/onboarding/conftest.py::fresh_login_page/primary_onboarded_page).
"""
import re

import allure
import pytest
from playwright.sync_api import Page, expect

from ui.pages.onboarding_page import OnboardingPage, NEXT_BUTTON, FINISH_BUTTON

from tests.ui.onboarding.locators import (
    KB_LINK,
    LIBRARY_TAB,
    FAVORITES_TAB,
    SUPPORT_LINK,
    SUPPORT_PLUS_ICON,
    PERSONAL_LINK,
    PERSONAL_SCHEDULE_TAB,
    MY_LEARNING_HEADING,
)

pytestmark = [pytest.mark.ui, pytest.mark.onboarding]


@allure.feature("Онбординг")
@allure.story("Первичный онбординг")
class TestPrimaryOnboarding:

    @allure.title("Первичный онбординг: модалка + «Интерактивное руководство» → «Моё обучение»")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_my_learning_first_time_onboarding(self, primary_onboarded_page: Page):
        page = primary_onboarded_page
        with allure.step("Пользователь остаётся на «Моё обучение»"):
            expect(page.get_by_role("heading", name=MY_LEARNING_HEADING)).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/education.*"), timeout=10000)

    @allure.title("Первичный онбординг раздела «База знаний» (Библиотека/Избранное)")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_knowledge_base_first_time_onboarding(self, primary_onboarded_page: Page):
        page = primary_onboarded_page
        onboarding = OnboardingPage(page)

        with allure.step("Открываем «База знаний» — запускается онбординг раздела"):
            kb_link = page.locator(KB_LINK).first
            expect(kb_link).to_be_visible(timeout=15000)
            kb_link.click(timeout=5000)

        with allure.step("Проходим онбординг раздела «База знаний»"):
            onboarding.complete_onboarding(max_steps=20)
            next_or_finish = page.locator(NEXT_BUTTON).or_(page.locator(FINISH_BUTTON))
            if next_or_finish.first.is_visible(timeout=10000):
                onboarding.complete_onboarding(max_steps=20)
            expect(page.locator(NEXT_BUTTON)).not_to_be_visible(timeout=10000)

        with allure.step("Открылась вкладка «Библиотека»"):
            expect(page.locator(LIBRARY_TAB)).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/library(?:/)?$"), timeout=10000)

        with allure.step("Переходим на вкладку «Избранное»"):
            favorites_tab = page.locator(FAVORITES_TAB)
            scrim = page.locator(".v-overlay__scrim").first
            if scrim.is_visible(timeout=1000):
                onboarding.complete_onboarding(max_steps=20)
            expect(favorites_tab).to_be_visible(timeout=15000)
            favorites_tab.click(timeout=5000)

        with allure.step("Проходим онбординг вкладки «Избранное», если он появился"):
            next_button = page.locator(NEXT_BUTTON)
            finish_button = page.locator(FINISH_BUTTON)
            steps = 0
            while next_button.is_visible(timeout=3000):
                next_button.click(timeout=5000)
                steps += 1
                assert steps <= 20, "Онбординг вкладки «Избранное» не закончился после 20 кликов"
            if finish_button.is_visible(timeout=3000):
                finish_button.click(timeout=5000)
            expect(next_button).not_to_be_visible(timeout=10000)

        with allure.step("Открыта вкладка «Избранное», список пуст"):
            expect(page.locator(FAVORITES_TAB)).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/library.*"), timeout=10000)
            expect(page.get_by_text("Вы пока ничего не добавили в Избранное")).to_be_visible(timeout=15000)

    @allure.title("После первичного онбординга доступна «Техподдержка»")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_support_page_after_onboarding(self, primary_onboarded_page: Page):
        page = primary_onboarded_page

        with allure.step("Открываем раздел «Техподдержка»"):
            support_link = page.locator(SUPPORT_LINK).first
            expect(support_link).to_be_visible(timeout=15000)
            support_link.click(timeout=5000, force=True)

        with allure.step("Доступна кнопка создания тикета «+»"):
            plus_icon = page.locator(SUPPORT_PLUS_ICON).first
            expect(plus_icon).to_be_visible(timeout=15000)

    @allure.title("Первичный онбординг раздела «Индивидуальное обучение»")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_personal_education_first_time_onboarding(self, primary_onboarded_page: Page):
        page = primary_onboarded_page
        onboarding = OnboardingPage(page)

        with allure.step("Открываем раздел «Индивидуальное обучение»"):
            personal_link = page.locator(PERSONAL_LINK).first
            expect(personal_link).to_be_visible(timeout=15000)
            personal_link.click(timeout=5000, force=True)

        with allure.step("Проходим онбординг раздела, если он появился"):
            status = onboarding.wait_for_primary_onboarding_or_repeat(timeout=5000)
            if status == "primary":
                onboarding.start_onboarding_if_present()
                onboarding.complete_onboarding(max_steps=30)

        with allure.step("Открыта страница «Индивидуальное обучение» с вкладкой «Расписание»"):
            expect(page.locator(PERSONAL_SCHEDULE_TAB).first).to_be_visible(timeout=15000)
            expect(page).to_have_url(re.compile(r".*/education/personal.*"), timeout=10000)
