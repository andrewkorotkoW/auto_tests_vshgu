import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External Content API")
@allure.story("Create & Activate External Content")
class TestExternalContentAPI:

    @allure.title("Создание, активация акивити игровой сессии")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_external_content_full_flow(self, api_client, external_system_client):
        from api.helpers.data_generator import generate_external_content_payload
        from api.endpoints.tincan import TincanEndpoint
        from api.endpoints.external_content import ExternalContentEndpoint

        ec_ep = ExternalContentEndpoint(api_client)

        with allure.step("1. Загрузить обложку"):
            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка: {cover_uuid}")

        with allure.step("2. Создать Активити"):
            payload = generate_external_content_payload(cover_uuid=cover_uuid)
            data = ec_ep.create(payload)
            content_id = data["id"]
            logger.info(f"Контент создан: ID={content_id}")

        with allure.step("3. Активировать активити"):
            activate_payload = {
                "data": {
                    "id": content_id,
                    "type": "content",
                    "attributes": {
                        "name": data["attributes"]["name"],
                        "content_type": "external_content",
                        "external_type": "simulator",
                        "cover_uuid": cover_uuid,
                        "description": data["attributes"]["description"],
                        "is_active": True
                    }
                }
            }
            ec_ep.activate(content_id, activate_payload)
            logger.info(f"Контент активирован: ID={content_id}")

        with allure.step("4. Активировать игровую сессию"):
            resp = external_system_client.post(f"/external/activities/{content_id}")
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text[:300], "Response", allure.attachment_type.TEXT)
            assert resp.status_code in (200, 201), f"Session activation failed: {resp.status_code} {resp.text}"
            logger.info(f"Игровая сессия активирована: {resp.text[:200]}")

        with allure.step("4.5. Повторная активация — 208"):
            resp2 = external_system_client.post(f"/external/activities/{content_id}")
            allure.attach(str(resp2.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp2.text[:300], "Response", allure.attachment_type.TEXT)
            assert resp2.status_code == 208, f"Ожидался 208, получен {resp2.status_code}"
            logger.info("Повторная активация вернула 208 (уже активирована)")

        with allure.step("5. Удалить внешний контент"):
            success = ec_ep.delete(content_id)
            assert success, f"Не удалось удалить контент {content_id}"
            logger.info(f"Контент удалён: ID={content_id}")