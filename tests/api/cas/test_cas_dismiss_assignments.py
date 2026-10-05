import allure
import pytest
import json
from api.endpoints.users import UsersEndpoint
from api.client import ApiClient
from config.settings import settings
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("External CAS API")
@allure.story("Dismiss Assignments")
class TestCasDismissAssignments:

    @allure.title("Снятие назначений с потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_dismiss_assignments(self, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import (
            generate_cas_payload, generate_external_cas_program_payload,
            generate_external_cas_stream_payload, generate_external_cas_user_payload
        )

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

        with allure.step("3. Создать двух пользователей и назначить"):
            user1 = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            user2 = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            uid1, uid2 = user1.get("user_id"), user2.get("user_id")

            external_cas_endpoint.assign_users(
                stream_id,
                [
                    {"user_id": uid1, "cas_application_uid": "dismiss-uid-1"},
                    {"user_id": uid2, "cas_application_uid": "dismiss-uid-2"}
                ],
                status="enlisted"
            )

        with allure.step("4. Снять назначения (dismissed)"):
            external_cas_endpoint.assign_users(
                stream_id,
                [
                    {"user_id": uid1, "cas_application_uid": "dismiss-uid-1"},
                    {"user_id": uid2, "cas_application_uid": "dismiss-uid-2"}
                ],
                status="dismissed"
            )

        with allure.step("5. Удалить назначения"):
            result = external_cas_endpoint.dismiss_assignments(stream_id, [uid1, uid2])
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Снятие", allure.attachment_type.JSON)
            logger.info("Назначения удалены")

        with allure.step("6. Очистка"):
            for uid in [uid1, uid2]:
                external_cas_endpoint.delete_user(uid)
                UsersEndpoint(ApiClient(cookie=settings.DEVELOP_COOKIE)).delete(uid)
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)

    @allure.title("Удаление назначений при наличии приказа — 422")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_dismiss_with_order_fails(self, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import (
            generate_cas_payload, generate_external_cas_program_payload,
            generate_external_cas_stream_payload, generate_external_cas_user_payload
        )

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

        with allure.step("3. Создать пользователя и назначить с приказом"):
            user = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            user_id = user.get("user_id")
            external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user_id, "cas_application_uid": "order-test-uid"}],
                status="enlisted",
                enlisted_text="Зачислен по приказу",
                enlisted_link="https://prikaz.ru/123"
            )

        with allure.step("4. Попытка удаления — 422"):
            resp = external_cas_endpoint.client.delete(
                "/external/cas/assignments",
                json={"stream_id": stream_id, "user_ids": [user_id]}
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response", allure.attachment_type.TEXT)
            expect_status(resp, 422)
            logger.info("Удаление с приказом отклонено (422)")

        with allure.step("5. Очистка"):
            external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user_id, "cas_application_uid": "order-test-uid"}],
                status="dismissed"
            )
            external_cas_endpoint.dismiss_assignments(stream_id, [user_id])
            external_cas_endpoint.delete_user(user_id)
            UsersEndpoint(ApiClient(cookie=settings.DEVELOP_COOKIE)).delete(user_id)
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)