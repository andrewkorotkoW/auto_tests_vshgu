import allure
import pytest
import json
import requests
from utils.logger import logger
from config.settings import settings
from api.helpers.expectations import expect_status


@allure.feature("External CAS API")
@allure.story("Create User")
class TestExternalCasUsersAPI:

    @allure.title("Создание пользователя CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_user(self, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_user_payload

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")
            logger.info(f"Связь CAS: ID={cas_id}")

        with allure.step("2. Создать пользователя"):
            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            allure.attach(json.dumps(user_payload, indent=2, ensure_ascii=False),
                         "Запрос", allure.attachment_type.JSON)

            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")

            allure.attach(json.dumps(user_data, indent=2, ensure_ascii=False),
                         "Ответ", allure.attachment_type.JSON)

            assert user_id, "user_id не должен быть пустым"
            logger.info(f"Пользователь CAS создан: user_id={user_id}, email={user_payload['email']}")


        with allure.step("3. Удалить синхронизацию пользователя CAS"):
            if user_id:
                success = external_cas_endpoint.delete_user(user_id)
                assert success, f"Не удалось удалить синхронизацию пользователя {user_id}"
                logger.info(f"Синхронизация пользователя CAS удалена: user_id={user_id}")

        with allure.step("3.5. Удалить пользователя"):
            from api.client import ApiClient
            from api.endpoints.users import UsersEndpoint
            main_client = ApiClient(cookie=settings.DEVELOP_COOKIE)
            UsersEndpoint(main_client).delete(user_id)
            logger.info(f"Пользователь удалён: user_id={user_id}")

        with allure.step("4. Удалить связь CAS"):
            if cas_id:
                omt_cas_endpoint.delete_tenant_org_location(cas_id)
                logger.info(f"Связь CAS удалена: ID={cas_id}")

    @allure.title("Создание пользователя CAS — несопоставленный тенант")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_create_user_unmatched_tenant(self, external_cas_endpoint):
        from api.helpers.data_generator import generate_external_cas_user_payload

        with allure.step("Создать пользователя с несуществующей связкой"):
            payload = generate_external_cas_user_payload(
                organization_uuid="00000000-0000-0000-0000-000000000000",
                location_uuid="00000000-0000-0000-0000-000000000000"
            )
            allure.attach(json.dumps(payload, indent=2, ensure_ascii=False),
                          "Запрос", allure.attachment_type.JSON)

            session = requests.Session()
            session.headers["Authorization"] = settings.CAS_AUTH_TOKEN
            session.headers["Accept"] = "application/json"
            session.headers["Content-Type"] = "application/json"
            session.cookies.set("develop", settings.DEVELOP_COOKIE)

            resp = session.post(f"{settings.BASE_URL}/external/cas/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response", allure.attachment_type.TEXT)

            expect_status(resp, 422)
            logger.info(f"Ошибка валидации (422): {resp.json().get('message', '')}")