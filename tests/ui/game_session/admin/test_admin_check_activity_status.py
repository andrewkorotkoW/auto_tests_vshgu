import allure
import pytest
from playwright.sync_api import expect
from ui.pages.admin_activities_page import AdminActivitiesPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("UI Tests")
@allure.story("Admin Check Status")
class TestAdminCheckActivityStatus:

    @allure.title("Проверка статуса активити в админке")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_activity_status(self, admin_page, env, api_client, external_system_client):
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
            expect_status(resp, (200, 201))
            logger.info("Игровая сессия активирована")

        # ========== UI ==========
        # admin_page — уже авторизованная под администратором страница (storage_state,
        # см. conftest._authenticated_page), поэтому логин через форму и клик по «Админка»
        # в меню пользователя (ui/pages/admin_page.py.go_to_admin — ненадёжен на develop,
        # см. фикс в этом же коммите) не нужны.
        with allure.step("4. Открыть «Базу Активити»"):
            UserSidebarPage(admin_page).dismiss_popups()
            activities_page = AdminActivitiesPage(admin_page)
            activities_page.open_list(env.ui_base_url)
            admin_page.screenshot(path="allure-results/admin_02_base.png")
            allure.attach.file("allure-results/admin_02_base.png", "База Активити", allure.attachment_type.PNG)

        with allure.step("5. Найти активити и проверить статус"):
            activities_page.expect_created(content_name)
            activities_page.row_by_name(content_name).locator("a[href*='/admin/activities/']").first.click()
            # Иконка статуса — inline SVG-кнопка (не icon-font i.mdi-check, как было раньше):
            # круглая v-btn--round со светло-зелёным фоном, применяемым чуть позже отрисовки
            # самой кнопки — поэтому expect(...).to_be_visible (с поллингом), а не is_visible().
            status_icon = admin_page.locator("button.v-btn--round[style*='213, 239, 209']")
            expect(status_icon).to_be_visible(timeout=10000)
            admin_page.screenshot(path="allure-results/admin_03_status.png")
            allure.attach.file("allure-results/admin_03_status.png", "Статус активен", allure.attachment_type.PNG)
            logger.info("Статус активити подтверждён")

        with allure.step("6. Очистка"):
            ec_ep.delete(content_id)
            logger.info(f"Контент удалён: ID={content_id}")
