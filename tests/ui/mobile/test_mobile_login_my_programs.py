"""Мобильная вёрстка (Pixel 7, --mobile/MOBILE=1): первый зелёный тест миссии —
«вход → список программ». Подготовка данных теми же API-фикстурами, что и в desktop
UI-тестах входа/списка программ (см. tests/ui/users/test_user_login_navigation.py,
tests/ui/practical_tasks/test_complete_practical_task.py): assigned_user — пользователь
назначен на поток (иначе «Моё обучение» показывает только 2 демо-карточки вместо
реально назначенной программы), prepare_user_for_tests_via_api закрывает блокирующую
модалку «данные о себе» и онбординг через API, без хрупкого прохождения тура в UI.

Facts: docs/mobile/layout_facts.md.
"""
import allure
import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Мобильная вёрстка")
@allure.story("Вход → список программ")
class TestMobileLoginMyPrograms:

    @allure.title("Мобильный (Pixel 7): слушатель входит и видит назначенную программу в списке")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.ui
    @pytest.mark.mobile
    def test_mobile_login_my_programs(self, page, env, api_client, assigned_user, is_mobile):
        assert is_mobile, "Тест должен запускаться с --mobile/MOBILE=1 — иначе он не проверяет мобильную вёрстку"
        allure.dynamic.parameter("device", "Pixel 7")

        with allure.step("1. Подготовить пользователя, назначенного на поток с программой"):
            assigned = assigned_user()
            user, stream = assigned["user"], assigned["stream"]
            prepare_user_for_tests_via_api(env, user["email"], user["password"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

        with allure.step(f"2. Войти слушателем '{user['email']}'"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False)
            UserSidebarPage(page).dismiss_popups()
            assert "/auth" not in page.url, page.url

        with allure.step("3. Список программ («Моё обучение») показывает назначенную программу"):
            task_page = PracticalTaskPage(page)
            task_page.open_programs_list(env.ui_base_url)
            expect_visible = task_page.program_title(program_name).first
            expect_visible.wait_for(state="visible", timeout=30000)
            page.screenshot(path="allure-results/mobile_my_programs.png")
            allure.attach.file("allure-results/mobile_my_programs.png", "Список программ (моб.)", allure.attachment_type.PNG)
