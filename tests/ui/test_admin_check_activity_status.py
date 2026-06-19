import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.admin_page import AdminPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Admin Check Status")
class TestAdminCheckActivityStatus:

    @allure.title("Проверка статуса активити в админке")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_activity_status(self, page, api_client, external_system_client):
        from api.helpers.data_generator import generate_external_content_payload
        from api.endpoints.tincan import TincanEndpoint
        from api.endpoints.external_content import ExternalContentEndpoint

        ec_ep = ExternalContentEndpoint(api_client)

        # ========== API ==========
        with allure.step("1. Создать внешний контент"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            payload = generate_external_content_payload(cover_uuid=cover_uuid)
            data = ec_ep.create(payload)
            content_id = data["id"]
            content_name = data["attributes"]["name"]
            logger.info(f"Контент создан: ID={content_id}, Name={content_name}")

        with allure.step("2. Активировать контент"):
            activate_payload = {
                "data": {
                    "id": content_id, "type": "content",
                    "attributes": {
                        "name": content_name,
                        "content_type": "external_content",
                        "external_type": "simulator",
                        "cover_uuid": cover_uuid,
                        "description": data["attributes"]["description"],
                        "is_active": True
                    }
                }
            }
            ec_ep.activate(content_id, activate_payload)
            logger.info("Контент активирован")

        with allure.step("3. Активировать игровую сессию"):
            resp = external_system_client.post(f"/external/activities/{content_id}")
            assert resp.status_code in (200, 201), f"Активация сессии не удалась: {resp.status_code}"
            logger.info("Игровая сессия активирована")

        # ========== UI ==========
        with allure.step("4. Логин под админом"):
            login_page = LoginPage(page)
            login_page.login("admin3@org2.ru", "SecurePass123")
            page.screenshot(path="allure-results/admin_01_login.png")
            allure.attach.file("allure-results/admin_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5. Перейти в Базу Активити"):
            admin_page = AdminPage(page)
            admin_page.go_to_admin()
            admin_page.open_activity_base()
            page.screenshot(path="allure-results/admin_02_base.png")
            allure.attach.file("allure-results/admin_02_base.png", "База Активити", allure.attachment_type.PNG)

        with allure.step("6. Найти активити и проверить статус"):
            admin_page.search_activity(content_name)
            admin_page.click_activity(content_name)
            admin_page.check_activity_status()
            page.screenshot(path="allure-results/admin_03_status.png")
            allure.attach.file("allure-results/admin_03_status.png", "Статус активен", allure.attachment_type.PNG)
            logger.info("Статус активити подтверждён")

        with allure.step("7. Очистка"):
            ec_ep.delete(content_id)
            logger.info(f"Контент удалён: ID={content_id}")