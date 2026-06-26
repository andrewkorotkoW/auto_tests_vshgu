import allure
import pytest
import json
from utils.logger import logger


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
            import time
            time.sleep(30)
            users_payload = [
                {**generate_cas_sync_payload(), "user_id": u["id"]} for u in users
            ]
            data = external_cas_endpoint.sync_users_bulk(users_payload)
            logger.info("Массовая синхронизация выполнена")
