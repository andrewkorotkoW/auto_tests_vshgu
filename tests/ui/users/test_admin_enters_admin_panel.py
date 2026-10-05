"""Перенос tests/ui/test_admin_login_and_go_to_admin.py коллеги (origin/feature/dashboard-autotests):
администратор входит через форму логина (а не через storage_state) и переходит в админ-панель."""
import re

import allure
import pytest
from playwright.sync_api import expect

from config.environments import get_credentials
from ui.pages.login_page import LoginPage


@allure.feature("Пользователи")
@allure.story("Вход администратора")
class TestAdminEntersAdminPanel:

    @allure.title("UI: администратор входит через форму логина и открывает админ-панель")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_enters_admin_panel(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Войти через форму логина под администратором"):
            LoginPage(page).login(email, password, base_url=env.ui_base_url, handle_onboarding=True)
            expect(page).not_to_have_url(re.compile(r".*/auth/(main|login)$"), timeout=30000)

        with allure.step("2. Открыть админ-панель"):
            page.goto(f"{env.ui_base_url.rstrip('/')}/admin/programs")
            expect(page).to_have_url(re.compile(r".*/admin/programs.*"), timeout=30000)
            expect(page).not_to_have_url(re.compile(r".*/(auth|404)"), timeout=5000)

        with allure.step("3. В админ-панели виден раздел «База Программ»"):
            expect(page.get_by_text("База Программ", exact=True).first).to_be_visible(timeout=30000)
