import allure
import pytest
from ui.pages.login_page import LoginPage
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
            # Учётные данные админа (замени на свои или бери из .env)
            admin_email = "admin3@org2.ru"
            admin_password = "SecurePass123"
            login_page = LoginPage(page)
            login_page.login(admin_email, admin_password)
            page.wait_for_timeout(3000)
            page.screenshot(path="allure-results/admin_role_ui_01_login.png")
            allure.attach.file("allure-results/admin_role_ui_01_login.png", "Логин админа", allure.attachment_type.PNG)

        with allure.step("3. Перейти в список пользователей"):
            # Открываем админку пользователей
            page.goto(f"{api_client.base_url.replace('/api/v1', '')}/admin/users")
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="allure-results/admin_role_ui_02_user_list.png")
            allure.attach.file("allure-results/admin_role_ui_02_user_list.png", "Список пользователей", allure.attachment_type.PNG)

        with allure.step("4. Найти пользователя и проверить роль"):
            # Явно ждём появления поля поиска (увеличим таймаут)
            search_input = page.locator("[data-qa='km-search']")
            search_input.wait_for(state="visible", timeout=15000)

            # Кликаем по полю для фокуса и очищаем (на случай, если там что-то есть)
            search_input.click()
            search_input.fill("")

            # Вводим полное имя (или email)
            full_name = f"{user['surname']} {user['name']}" if user.get('surname') else user['name']
            search_input.fill(full_name)

            # Небольшая пауза, чтобы поиск отработал
            page.wait_for_timeout(2000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)

            # Ждём появления хотя бы одной строки в таблице (как признак, что поиск завершён)
            try:
                page.wait_for_selector("table tbody tr", timeout=10000)
            except:
                pass

            # Пытаемся найти строку с именем или email
            user_row = page.locator(f"tr:has-text('{full_name}')").first
            if user_row.count() == 0:
                user_row = page.locator(f"tr:has-text('{user['email']}')").first

            # Если всё ещё не нашли — делаем скриншот для диагностики
            if user_row.count() == 0:
                page.screenshot(path="allure-results/admin_role_ui_search_failed.png")
                allure.attach.file("allure-results/admin_role_ui_search_failed.png", "Результат поиска",
                                   allure.attachment_type.PNG)
                logger.error(f"Пользователь {full_name} не найден. Проверьте скриншот.")

            assert user_row.count() > 0, f"Пользователь {full_name} не найден в списке"

            # Проверяем роль
            role_cell = user_row.locator("td:has-text('Преподаватель')")
            assert role_cell.count() > 0, "Роль 'Преподаватель' не отображается у пользователя"
            logger.info("Роль 'Преподаватель' успешно отображается в админке")

            page.screenshot(path="allure-results/admin_role_ui_03_role_visible.png")
            allure.attach.file("allure-results/admin_role_ui_03_role_visible.png", "Роль отображается",
                               allure.attachment_type.PNG)