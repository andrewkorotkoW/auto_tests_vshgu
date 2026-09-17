import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.admin_page import AdminPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Admin CAS Users")
class TestAdminCasUsers:

    @allure.title("Админ: проверка CAS-пользователя в Базе Пользователей")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_cas_user(self, page, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_user_payload

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать CAS-пользователя"):
            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")
            user_fio = f"{user_payload['surname']} {user_payload['name']} {user_payload['patronymic']}"
            logger.info(f"CAS пользователь: ID={user_id}, ФИО={user_fio}")

        # ========== UI ==========
        with allure.step("3. Логин под админом"):
            login_page = LoginPage(page)
            login_page.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)
            page.wait_for_timeout(3000)

        with allure.step("4. Перейти в Базу Пользователей"):
            admin_page = AdminPage(page)
            admin_page.go_to_admin()
            page.locator("div.v-list-item__title:has-text('База Пользователей')").first.click(force=True)
            page.wait_for_timeout(2000)

        with allure.step("5. Найти пользователя по ФИО"):
            page.locator('[data-qa="km-search"]').fill(user_fio)
            page.wait_for_timeout(1000)
            page.locator(f"text={user_fio}").first.click(force=True)
            page.wait_for_timeout(2000)
            page.screenshot(path="allure-results/cas_admin_user.png")
            allure.attach.file("allure-results/cas_admin_user.png", "Пользователь КАС", allure.attachment_type.PNG)

        with allure.step("6. Проверить тип регистрации — КАС"):
            assert page.locator("text=КАС").first.is_visible(timeout=5000), "Тип регистрации не КАС!"
            logger.info("Тип регистрации: КАС подтверждён")

        with allure.step("7. Проверить статус синхронизации"):
            # Проверить текст "Синхронизирован"
            synced_chip = page.locator("span.v-chip__content:has-text('Синхронизирован')")
            assert synced_chip.first.is_visible(timeout=5000), "Статус 'Синхронизирован' не отображается!"

            # Проверить заголовок "Синхронизация с КАС"
            assert page.locator("text=Синхронизация с КАС").first.is_visible(timeout=3000), "Заголовок не отображается!"

            logger.info("Синхронизация с КАС подтверждена")
            page.screenshot(path="allure-results/cas_admin_user_synced.png")
            allure.attach.file("allure-results/cas_admin_user_synced.png", "Синхронизация КАС",
                               allure.attachment_type.PNG)

        with allure.step("7.1. Снять синхронизацию (API)"):
            external_cas_endpoint.delete_user(user_id)
            logger.info("Синхронизация снята")

        with allure.step("7.2. Обновить страницу и проверить отсутствие синхронизации"):
            page.reload()
            page.wait_for_timeout(2000)
            # Повторный поиск
            page.locator('[data-qa="km-search"]').fill(user_fio)
            page.wait_for_timeout(1000)
            page.locator(f"text={user_fio}").first.click(force=True)
            page.wait_for_timeout(2000)

            assert not page.locator("span.v-chip__content:has-text('Синхронизирован')").first.is_visible(
                timeout=5000), "Синхронизация не снята!"
            page.screenshot(path="allure-results/cas_admin_user_unsynced.png")
            allure.attach.file("allure-results/cas_admin_user_unsynced.png", "Синхронизация снята",
                               allure.attachment_type.PNG)
            logger.info("Синхронизация снята — статус исчез")

        # ========== CLEANUP ==========
        with allure.step("8. Очистка"):
            # Снять синхронизацию (если ещё не снята)
            external_cas_endpoint.delete_user(user_id)
            # Удалить обычного пользователя
            from api.endpoints.users import UsersEndpoint
            from api.client import ApiClient
            from config.settings import settings
            main_client = ApiClient(cookie=settings.DEVELOP_COOKIE)
            UsersEndpoint(main_client).delete(user_id)
            logger.info(f"Пользователь удалён: ID={user_id}")
            # Удалить связь CAS
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info("Очистка завершена")