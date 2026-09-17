import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External CAS API")
@allure.story("Assign Users")
class TestExternalCasAssignAPI:

    @allure.title("Назначение пользователей на поток CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_assign_users(self, omt_cas_endpoint, external_cas_endpoint, created_user):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_program_payload, generate_external_cas_stream_payload

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу и поток"):
            data = external_cas_endpoint.create_program(
                generate_external_cas_program_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            program_id = data.get("program_id")
            stream_data = external_cas_endpoint.create_stream(program_id, generate_external_cas_stream_payload())
            stream_id = stream_data.get("stream_id")

        with allure.step("3. Создать пользователей"):
            user1 = created_user()
            user2 = created_user()

        with allure.step("4. Назначить пользователей на поток"):
            user_ids = [
                {"user_id": user1["id"], "cas_application_uid": "a1111111-bbbb-cccc-dddd-eeeeeeeeeee1"},
                {"user_id": user2["id"], "cas_application_uid": "a2222222-bbbb-cccc-dddd-eeeeeeeeeee2"}
            ]
            result = external_cas_endpoint.assign_users(stream_id, user_ids)
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Назначение", allure.attachment_type.JSON)
            logger.info(f"Пользователи назначены: {result}")

        with allure.step("5. Очистка"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)

    @allure.title("Снятие назначения пользователя с потока CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_dismiss_users(self, omt_cas_endpoint, external_cas_endpoint, created_user):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_program_payload, generate_external_cas_stream_payload

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу и поток"):
            data = external_cas_endpoint.create_program(
                generate_external_cas_program_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            program_id = data.get("program_id")
            stream_data = external_cas_endpoint.create_stream(program_id, generate_external_cas_stream_payload())
            stream_id = stream_data.get("stream_id")

        with allure.step("3. Создать CAS-пользователя"):
            from api.helpers.data_generator import generate_external_cas_user_payload
            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")
            logger.info(f"CAS пользователь: ID={user_id}")

        with allure.step("4. Назначить пользователя"):
            user_ids = [{"user_id": user_id, "cas_application_uid": "a1111111-bbbb-cccc-dddd-eeeeeeeeeee1"}]
            external_cas_endpoint.assign_users(stream_id, user_ids, status="enlisted")

        with allure.step("5. Снять назначение (dismissed)"):
            result = external_cas_endpoint.assign_users(
                stream_id, user_ids,
                status="dismissed",
                dismissed_text="Причина отчисления",
                dismissed_link="https://example.com/dismiss"
            )
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Снятие", allure.attachment_type.JSON)
            logger.info(f"Назначение снято: {result}")

        import time
        # Ожидание без условия: асинхронная обработка dismiss в CAS не имеет статус-эндпоинта для поллинга.
        time.sleep(60)

        with allure.step("6. Очистка"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)