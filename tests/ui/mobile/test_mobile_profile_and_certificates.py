"""Мобильная вёрстка (Pixel 7): слушатель открывает «Профиль» (нижняя панель вкладок)
и пробует увидеть вкладку «Мои сертификаты».

Разведка 06.10 (michael/dwight) считала, что после клика по «Профиль» висит бесконечный
спиннер; перепроверка 07.10 на develop: клик с /education ведёт на /profile/<id>, содержимое
отрисовывается за ~3 с без спиннера и ошибок в сети — ошибкой было ожидание email, которого
на мобильной вкладке «Профиль» нет. Page object для раздела «Профиль» не существует и на
desktop, поэтому локаторы нижней панели здесь напрямую.
"""
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
                # Клик сразу после загрузки /education — no-op (обработчик нижней панели ещё не
                # навешан, URL не меняется — так и родилась версия про «бесконечный спиннер»).
                # Ждём тишины в сети, кликаем и проверяем переход на /profile/<id>; при no-op —
                # один повторный клик.
                page.wait_for_load_state("networkidle", timeout=15000)
                for _ in range(2):
                    profile_tab.click()
                    try:
                        expect(page).to_have_url(re.compile(r".*/profile/\d+.*"), timeout=10000)
                        break
                    except AssertionError:
                        continue
                expect(page).to_have_url(re.compile(r".*/profile/\d+.*"), timeout=5000)

            with allure.step("5. Содержимое вкладки «Профиль» должно отрисоваться (ФИО, роль «Слушатель»)"):
                # На мобильной вкладке «Профиль» email не показывается (только ФИО, роль, регион,
                # QR-код, рассылка) — проверено 07.10 на develop, см. layout_facts.md п.5.
                expect(page.get_by_text(user["surname"], exact=False).first).to_be_visible(timeout=20000)
                expect(page.get_by_text("Слушатель", exact=True).first).to_be_visible(timeout=10000)

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
