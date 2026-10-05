import allure
import pytest
import json
from utils.logger import logger
from api.helpers.data_generator import (generate_cas_payload, generate_external_cas_program_payload,
                                        generate_external_cas_stream_payload)


@allure.feature("External CAS API")
@allure.story("Create Program")
class TestExternalCasAPI:

    @allure.title("Создание и удаление программы CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_program(self, api_client, omt_cas_endpoint, external_cas_endpoint):

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")
            allure.attach(json.dumps(cas_data, indent=2, ensure_ascii=False), "Связь CAS", allure.attachment_type.JSON)
            logger.info(f"Связь CAS создана: ID={cas_id}")

        with allure.step("2. Создать программу"):
            program_payload = generate_external_cas_program_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            data = external_cas_endpoint.create_program(program_payload)
            program_id = data.get("program_id")
            allure.attach(json.dumps(data, indent=2, ensure_ascii=False), "Программа создана", allure.attachment_type.JSON)
            logger.info(f"Программа создана: ID={program_id}")

        with allure.step("3. Создать поток"):
            stream_payload = generate_external_cas_stream_payload()
            stream_data = external_cas_endpoint.create_stream(program_id, stream_payload)
            stream_id = stream_data.get("stream_id")
            allure.attach(json.dumps(stream_data, indent=2, ensure_ascii=False), "Поток создан", allure.attachment_type.JSON)
            logger.info(f"Поток создан: ID={stream_id}")

            from datetime import datetime, timedelta

            today = datetime.now()
            date_from = today.strftime("%Y-%m-%d")
            date_to = (today.replace(day=20) + timedelta(days=32)).replace(day=20).strftime("%Y-%m-%d")

            with allure.step("4. Обновить поток"):
                updated = external_cas_endpoint.update_stream(program_id, stream_id, date_from, date_to)
            allure.attach(json.dumps(updated, indent=2, ensure_ascii=False), "Поток обновлён", allure.attachment_type.JSON)
            logger.info(f"Поток обновлён: {updated}")

        with allure.step("5. Снять синхронизацию потока"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            logger.info(f"Синхронизация потока снята: ID={stream_id}")

        with allure.step("6. Снять синхронизацию программы"):
            external_cas_endpoint.delete_program(program_id)
            logger.info(f"Синхронизация программы снята: ID={program_id}")

        with allure.step("7. Удалить программу"):
            from api.endpoints.programs import ProgramsEndpoint
            ProgramsEndpoint(api_client).mass_delete([program_id])
            logger.info(f"Программа удалена: ID={program_id}")

        with allure.step("8. Удалить связь CAS"):
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info(f"Связь CAS удалена: ID={cas_id}")
        with allure.step("10. Снять синхронизацию потока (API)"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            logger.info("Синхронизация потока снята")
