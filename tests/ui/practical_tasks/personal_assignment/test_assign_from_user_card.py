"""Индивидуальное назначение ПЗ из карточки пользователя: поиск по email в «База
Пользователей», вкладка «Назначения», модалка «Добавить Активити».

Перенос сценариев test_10/test_11 коллеги (репозиторий lms, feature/my-tests, см.
report.md разд. 2). Пользователь и ПЗ подняты через наши API-фикстуры created_user/
created_homework; UI — только поиск и назначение из карточки пользователя.
"""
import allure
import pytest

from ui.pages.admin_users_page import AdminUsersPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("Практические задания UI")
@allure.story("Индивидуальное назначение: из карточки пользователя")
class TestAssignFromUserCard:

    @allure.title("UI: Администратор назначает ПЗ пользователю из карточки (вкладка «Назначения»)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_assign_from_user_card(self, admin_page, env, created_user, created_homework, homework_endpoint):
        homework_id = None

        try:
            with allure.step("1. Подготовить пользователя и ПЗ через API"):
                user = created_user()
                homework = created_homework()
                homework_id = homework["id"]
                logger.info(f"Пользователь: {user['id']} ({user['email']}), ПЗ: {homework_id} ({homework['name']})")

            with allure.step(f"2. Найти пользователя по email '{user['email']}' в «База Пользователей»"):
                admin_page.goto(f"{env.ui_base_url}/admin/users")
                # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
                # закрываем его, иначе затемнение перехватывает клики и networkidle не наступает
                UserSidebarPage(admin_page).dismiss_popups()
                users_page = AdminUsersPage(admin_page)
                users_page.search_by_email(user["email"])

            with allure.step("3. Открыть карточку пользователя и вкладку «Назначения»"):
                users_page.open_user_by_email(user["email"])
                users_page.open_assignments_tab()

            with allure.step(f"4. Назначить ПЗ '{homework['name']}' через модалку «Добавить Активити»"):
                users_page.add_activity_to_user(homework["name"])
        finally:
            if homework_id is not None:
                with allure.step("5. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
