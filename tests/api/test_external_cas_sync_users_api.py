import allure
import pytest
import json
from utils.logger import logger
from api.helpers.data_generator import generate_cas_sync_payload


@allure.feature("External CAS API")
@allure.story("Sync User")

class TestExternalCasSyncUsersAPI:

    @allure.title("Синхронизация существующего пользователя с CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_sync_user(self, created_user, external_cas_endpoint):

        with allure.step("1. Создать пользователя"):
            user = created_user()
            user_id = user["id"]
            logger.info(f"Пользователь: ID={user_id}, email={user['email']}")

        with allure.step("2. Синхронизировать пользователя"):
            import time
            time.sleep(20)
            sync_payload = generate_cas_sync_payload()
            logger.info(f"sync_payload cas_uuid: {sync_payload.get('cas_uuid')}")
            logger.info(f"Full sync_payload: {sync_payload}")
            data = external_cas_endpoint.sync_user(user_id, sync_payload)

        with allure.step("3. Снять синхронизацию"):
            external_cas_endpoint.delete_user(user_id)
            logger.info(f"Синхронизация снята: user_id={user_id}")