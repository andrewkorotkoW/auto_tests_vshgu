import allure
import pytest
import json
import time
import random
from utils.logger import logger
from api.endpoints.users import UsersEndpoint
from api.client import ApiClient
from config.settings import settings


@allure.feature("External CAS API")
@allure.story("Export Assignments")
class TestExternalCasExportAPI:

    @allure.title("Экспорт назначений CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_export_assignments(self, omt_cas_endpoint, external_cas_endpoint):
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

        with allure.step("3. Создать пользователя и назначить"):
            user = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            user_id = user.get("user_id")
            app_uid = f"export-{int(time.time())}-{random.randint(1000, 9999)}-{stream_id}"

            result = external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user_id, "cas_application_uid": app_uid}],
                status="enlisted"
            )
            logger.info(f"Assign result: {result}")
            logger.info(f"Пользователь {user_id} назначен на поток {stream_id}")

        with allure.step("4. Экспорт назначений"):
            export_data = external_cas_endpoint.export_assignments([app_uid], stream_id)
            allure.attach(json.dumps(export_data, indent=2, ensure_ascii=False), "Экспорт", allure.attachment_type.JSON)
            logger.info(f"Экспорт выполнен")

        with allure.step("5. Очистка"):
            # Снять синхронизации CAS
            external_cas_endpoint.delete_user(user_id)
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            # Реально удалить
            UsersEndpoint(ApiClient(cookie=settings.DEVELOP_COOKIE)).delete(user_id)
            from api.endpoints.programs import ProgramsEndpoint
            ProgramsEndpoint(ApiClient(cookie=settings.DEVELOP_COOKIE)).mass_delete([program_id])
            # Удалить связь CAS
            omt_cas_endpoint.delete_tenant_org_location(cas_id)