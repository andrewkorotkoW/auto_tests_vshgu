import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.admin_users_page import AdminUsersPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger
from api.endpoints.users import UsersEndpoint


@allure.feature("Users UI")
@allure.story("Admin verifies assigned role")
class TestAdminVerifyRoleUI:

    @allure.title("Администратор проверяет роль 'Преподаватель' у пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_admin_sees_teacher_role(self, page, api_client, created_user):
        users_ep = UsersEndpoint(api_client)

        with allure.step("1. Создать пользователя и назначить роль teacher"):
            user = created_user()
            logger.info(f"Пользователь создан: ID={user['id']}, email={user['email']}")
            users_ep.assign_roles(user["id"], [4])  # 4 — ID роли teacher
            logger.info("Роль teacher назначена")

        with allure.step("2. Логин под администратором"):
            admin_email = settings.TEST_USER_EMAIL
            admin_password = settings.TEST_USER_PASSWORD
            login_page = LoginPage(page)
            login_page.login(admin_email, admin_password)
            page.screenshot(path="allure-results/admin_role_ui_01_login.png")
            allure.attach.file("allure-results/admin_role_ui_01_login.png", "Логин админа", allure.attachment_type.PNG)

        with allure.step("3. Перейти в список пользователей"):
            # Онбординг-тур ещё не пройден на этой странице — его затемнение перехватывает
            # клики и не даёт странице дойти до networkidle (на чём падает AdminUsersPage.open),
            # поэтому закрываем его сразу после навигации.
            admin_users_page = AdminUsersPage(page)
            page.goto(f"{settings.UI_BASE_URL}{admin_users_page.PATH}")
            UserSidebarPage(page).dismiss_popups()
            admin_users_page.page.locator('[data-qa="km-search"]').first.wait_for(state="visible", timeout=30000)
            page.screenshot(path="allure-results/admin_role_ui_02_user_list.png")
            allure.attach.file("allure-results/admin_role_ui_02_user_list.png", "Список пользователей", allure.attachment_type.PNG)

        with allure.step("4. Найти пользователя и открыть карточку"):
            # В таблице «База Пользователей» нет колонки «Роль» — роль отображается
            # только на карточке пользователя. Сначала ищем по email (иначе только
            # что созданного пользователя не будет на первой странице списка).
            admin_users_page.search_by_email(user["email"])
            admin_users_page.open_user_by_email(user["email"])
            page.screenshot(path="allure-results/admin_role_ui_03_user_card.png")
            allure.attach.file("allure-results/admin_role_ui_03_user_card.png", "Карточка пользователя",
                               allure.attachment_type.PNG)

        with allure.step("5. Проверить роль"):
            role_element = page.locator("text=Преподаватель").first
            expect(role_element).to_be_visible(timeout=15000)
            logger.info("Роль 'Преподаватель' успешно отображается в админке")

            page.screenshot(path="allure-results/admin_role_ui_04_role_visible.png")
            allure.attach.file("allure-results/admin_role_ui_04_role_visible.png", "Роль отображается",
                               allure.attachment_type.PNG)