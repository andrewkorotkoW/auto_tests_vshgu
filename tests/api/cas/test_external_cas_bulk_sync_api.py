import allure
import pytest
import json
from api.helpers.expectations import expect_status
from utils.logger import logger
from utils.retry import retry_until_success


@allure.feature("External CAS API")
@allure.story("Bulk Sync Users")
class TestExternalCasBulkSyncAPI:

    @allure.title("Массовая синхронизация пользователей")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_bulk_sync_users(self, external_cas_endpoint, created_user):
        from api.helpers.data_generator import generate_cas_sync_payload

        with allure.step("1. Создать 3 пользователей"):
            users = [created_user() for _ in range(3)]
            for u in users:
                logger.info(f"Пользователь: ID={u['id']}")

        with allure.step("2. Массовая синхронизация"):
            users_payload = [
                {**generate_cas_sync_payload(), "user_id": u["id"]} for u in users
            ]
            # Статус-эндпоинта индексации новых пользователей нет — вместо слепой паузы
            # повторяем саму синхронизацию, пока бэкенд её не примет (обычно с первого раза).
            resp = retry_until_success(
                lambda: external_cas_endpoint.client.post("/external/cas/sync/users", json=users_payload),
                timeout=60, interval=5, success_codes=(200, 201),
            )
            expect_status(resp, (200, 201))
            data = resp.json().get("data", resp.json())
            logger.info("Массовая синхронизация выполнена")
