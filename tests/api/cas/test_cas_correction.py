import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External CAS API")
@allure.story("Correction Sync")
class TestCasCorrection:

    @allure.title("Корректировка синхронизации потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_correction_sync(self, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import (
            generate_cas_payload, generate_external_cas_program_payload,
            generate_external_cas_stream_payload, generate_stream_payload
        )
        from api.endpoints.streams import StreamsEndpoint

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу CAS + поток CAS"):
            data = external_cas_endpoint.create_program(
                generate_external_cas_program_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            program_id = data.get("program_id")
            stream_cas = external_cas_endpoint.create_stream(program_id, generate_external_cas_stream_payload())
            source_stream_id = stream_cas.get("stream_id")

        with allure.step("3. Создать обычный поток"):
            stream_data = StreamsEndpoint(api_client).create(program_id, generate_stream_payload())
            stream_id = stream_data["id"]
            logger.info(f"Обычный поток: ID={stream_id}")

        with allure.step("4. Корректировка синхронизации"):
            result = external_cas_endpoint.correct_sync(program_id, stream_id, program_id, source_stream_id)
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Корректировка", allure.attachment_type.JSON)
            logger.info("Корректировка выполнена")
