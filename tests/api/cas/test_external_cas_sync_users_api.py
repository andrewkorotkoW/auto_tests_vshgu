import allure
import pytest
import json
from utils.logger import logger
from api.helpers.data_generator import (
    generate_cas_payload,
    generate_cas_sync_payload,
    generate_external_cas_user_payload,
)


@allure.feature("External CAS API")
@allure.story("Sync User")

class TestExternalCasSyncUsersAPI:

    @allure.title("Синхронизация существующего пользователя с CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_sync_user(self, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.endpoints.users import UsersEndpoint

        with allure.step("1. Создать пользователя"):
            # POST /external/cas/sync/users/{id} синхронизирует только пользователя,
            # уже известного CAS (есть связанная cas-запись) — обычный пользователь,
            # созданный через UsersEndpoint.create (без связи CAS), стабильно отдаёт
            # 400 "Синхронизация для пользователя недоступна" (user_status: pending)
            # независимо от ожидания: проверено прямыми запросами к API — это не
            # индексация, а отсутствие предусловия. Поэтому готовим предусловие сами:
            # создаём связь CAS и CAS-пользователя (как test_cas_update_user), затем
            # снимаем синхронизацию, чтобы шаг 2 проверял именно повторную
            # синхронизацию уже существующего пользователя, а не его создание.
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"],
            )
            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")
            logger.info(f"Пользователь: ID={user_id}")

            external_cas_endpoint.delete_user(user_id)

        with allure.step("2. Синхронизировать пользователя"):
            sync_payload = generate_cas_sync_payload()
            logger.info(f"sync_payload cas_uuid: {sync_payload.get('cas_uuid')}")
            logger.info(f"Full sync_payload: {sync_payload}")
            data = external_cas_endpoint.sync_user(user_id, sync_payload)
            assert data.get("sync_status") == "synced", f"Статус после синхронизации не synced: {data}"

        with allure.step("3. Снять синхронизацию"):
            external_cas_endpoint.delete_user(user_id)
            logger.info(f"Синхронизация снята: user_id={user_id}")

        with allure.step("4. Очистка"):
            UsersEndpoint(api_client).delete(user_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)