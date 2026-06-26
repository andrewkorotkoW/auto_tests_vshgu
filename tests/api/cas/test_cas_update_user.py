import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External CAS API")
@allure.story("Update User")
class TestCasUpdateUser:

    @allure.title("Обновление CAS-пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_update_cas_user(self, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import (
            generate_cas_payload, generate_external_cas_user_payload
        )

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
            logger.info(f"Пользователь создан: ID={user_id}")

        with allure.step("3. Обновить пользователя"):
            update_payload = {
                "name": "Обновлённое_Имя",
                "patronymic": user_payload["patronymic"],
                "surname": user_payload["surname"],
                "date_of_birth": user_payload["date_of_birth"],
                "personal_phone_number": user_payload["personal_phone_number"],
                "organisation": user_payload["organisation"],
                "position": user_payload["position"],
                "region": user_payload["region"]
            }
            # Нужен метод update_user в ExternalCasEndpoint
            result = external_cas_endpoint.update_user(user_id, update_payload)
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Обновление", allure.attachment_type.JSON)
            logger.info(f"Пользователь обновлён")

        with allure.step("4. Очистка"):
            external_cas_endpoint.delete_user(user_id)
            from api.endpoints.users import UsersEndpoint
            from api.client import ApiClient
            from config.settings import settings
            UsersEndpoint(ApiClient(cookie=settings.DEVELOP_COOKIE)).delete(user_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)