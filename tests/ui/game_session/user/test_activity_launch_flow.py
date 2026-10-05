import re

import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.activity_page import ActivityPage
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("UI Tests")
@allure.story("Activity Launch Flow")
class TestActivityLaunchFlow:

    @allure.title("E2E: Создание → Активация → Запуск активити")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_activity_launch(self, page, api_client, created_user, created_program,
                              created_stream, created_module, assignments_endpoint,
                              external_system_client):
        from api.helpers.data_generator import generate_external_content_payload
        from api.endpoints.tincan import TincanEndpoint
        from api.endpoints.external_content import ExternalContentEndpoint

        ec_ep = ExternalContentEndpoint(api_client)

        # ========== API ==========
        with allure.step("1. Создать программу"):
            program = created_program(name="E2E_Activity_Launch")

        with allure.step("2. Создать поток"):
            stream = created_stream(program_id=program["id"])

        with allure.step("3. Создать модуль"):
            module = created_module(program_id=program["id"], stream_id=stream["id"])

        with allure.step("4. Создать пользователя"):
            user = created_user()

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

        with allure.step("6. Создать внешний контент"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            payload = generate_external_content_payload(cover_uuid=cover_uuid)
            data = ec_ep.create(payload)
            content_id = data["id"]
            content_name = data["attributes"]["name"]

        with allure.step("7. Активировать контент"):
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

        with allure.step("8. Активировать игровую сессию"):
            resp = external_system_client.post(f"/external/activities/{content_id}")
            expect_status(resp, (200, 201))

        with allure.step("9. Назначить активити в модуль"):
            ec_ep.assign_to_module(program["id"], stream["id"], module["id"], [content_id])

        # ========== UI ==========
        with allure.step("10. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/launch_01_login.png")

        with allure.step("11. Открыть программу и запустить активити"):
            activity_page = ActivityPage(page)
            activity_page.start_external_activity(program["name"])
            # Итог прохождения: клик по «Начать» переводит на подстраницу игровой сессии
            # модуля (.../module/{id}/external) — раньше тест не проверял результат запуска
            # вообще, поэтому мог годами оставаться зелёным при сломанной кнопке.
            expect(page).to_have_url(re.compile(r".*/module/\d+/external.*"), timeout=15000)
            page.screenshot(path="allure-results/launch_02_started.png")
            logger.info(f"Активити запущена, URL={page.url}")

        with allure.step("12. Очистка"):
            ec_ep.delete(content_id)
            logger.info(f"Контент удалён: {content_id}")

        logger.info("E2E Activity Launch завершён!")



