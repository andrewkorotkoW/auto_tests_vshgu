"""Мобильная вёрстка (Pixel 7): слушатель открывает «Профиль» (нижняя панель вкладок)
и пробует увидеть вкладку «Мои сертификаты».

xfail: см. docs/mobile/layout_facts.md п.5 — клик по нижней вкладке «Профиль» не меняет
URL (переключение внутреннего состояния SPA, не роутер) и работает только со страницы
«Моё обучение» (/education корень); после клика содержимое вкладки «Профиль» не
отрисовывается — бесконечный спиннер `.v-progress-circular` (воспроизведено дважды в
разведке michael/dwight). Нет ни одного UI page object/селектора для раздела
«Профиль»/«Мои сертификаты» даже на desktop (grep по ui/pages/*.py ничего не находит) —
дописывать его в рамках этой задачи не предмет (задача запрещает новые/переработанные
page objects), поэтому тест фиксирует наблюдаемое поведение напрямую через локаторы
нижней панели и общий спиннер, а не новый метод в page object.

Данные — assigned_user + prepare_user_for_tests_via_api, как и в остальных мобильных
тестах набора (тот же способ подготовки «данных о себе», без которого онбординг
блокирует страницу)."""
import re

import allure
import pytest
from playwright.sync_api import expect

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Мобильная вёрстка")
@allure.story("Профиль и сертификаты")
class TestMobileProfileAndCertificates:

    @allure.title("Мобильный (Pixel 7): вкладка «Профиль» нижней панели — ожидаемый дефект вёрстки")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.mobile
    @pytest.mark.xfail(
        reason=(
            "Мобильная вкладка «Профиль» (нижняя панель, a.bottom-bar__link) после клика "
            "с /education не отрисовывает содержимое — бесконечный спиннер "
            ".v-progress-circular, подтверждено в разведке (docs/mobile/layout_facts.md п.5); "
            "«Мои сертификаты» как подвкладка профиля недостижима тем же путём. Кандидат в "
            "дефект мобильной вёрстки, не ошибка теста."
        ),
        strict=False,
    )
    def test_mobile_profile_tab_shows_content(self, page, env, api_client, prepared_user, is_mobile):
        assert is_mobile, "Тест должен запускаться с --mobile/MOBILE=1 — иначе он не проверяет мобильную вёрстку"
        allure.dynamic.parameter("device", "Pixel 7")

        try:
            with allure.step("1. Подготовить слушателя через API"):
                user = prepared_user()

            with allure.step(f"2. Войти слушателем '{user['email']}'"):
                LoginPage(page).login(
                    user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False
                )
                UserSidebarPage(page).dismiss_popups()

            with allure.step("3. Открыть «Моё обучение» (/education) — обязательная точка входа в «Профиль»"):
                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                expect(page).to_have_url(re.compile(r".*/education.*"), timeout=15000)

            with allure.step("4. Клик по вкладке «Профиль» нижней панели"):
                profile_tab = page.locator("a.bottom-bar__link", has_text="Профиль").first
                expect(profile_tab).to_be_visible(timeout=15000)
                profile_tab.click(force=True)

            with allure.step("5. Содержимое вкладки «Профиль» должно отрисоваться (ФИО/email)"):
                expect(page.get_by_text(user["email"], exact=False)).to_be_visible(timeout=20000)

            with allure.step("6. Открыть подвкладку «Мои сертификаты»"):
                certificates_tab = page.locator("xpath=//span[normalize-space()='Мои сертификаты']").first
                expect(certificates_tab).to_be_visible(timeout=15000)
                certificates_tab.click(force=True)
                expect(page.locator(".v-progress-circular")).to_have_count(0, timeout=20000)
        finally:
            with allure.step("7. Скриншот текущего состояния экрана (вёрстка Pixel 7)"):
                page.screenshot(path="allure-results/mobile_profile.png")
                allure.attach.file(
                    "allure-results/mobile_profile.png", "Профиль (моб.)", allure.attachment_type.PNG
                )
