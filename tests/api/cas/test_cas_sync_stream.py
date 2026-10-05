import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External CAS API")
@allure.story("Sync Stream")
class TestCasSyncStream:

    @allure.title("Синхронизация обычного потока с CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_sync_regular_stream(self, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_program_payload, generate_stream_payload
        from api.endpoints.streams import StreamsEndpoint

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу через CAS"):
            data = external_cas_endpoint.create_program(
                generate_external_cas_program_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            program_id = data.get("program_id")

        with allure.step("3. Создать обычный поток"):
            stream_data = StreamsEndpoint(api_client).create(program_id, generate_stream_payload())
            stream_id = stream_data["id"]
            logger.info(f"Обычный поток: ID={stream_id}")

        with allure.step("4. Синхронизировать поток с CAS"):
            result = external_cas_endpoint.sync_stream(program_id, stream_id)
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Синхронизация", allure.attachment_type.JSON)
            logger.info(f"Поток синхронизирован")

        with allure.step("5. Очистка"):
            StreamsEndpoint(api_client).delete(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)