import allure
import pytest
import json
from utils.logger import logger


@allure.feature("External CAS API")
@allure.story("Sync Program")
class TestCasSyncProgram:

    @allure.title("Синхронизация обычной программы с CAS")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_sync_regular_program(self, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_program_payload
        from api.endpoints.programs import ProgramsEndpoint

        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать обычную программу"):
            prog_data = ProgramsEndpoint(api_client).create(
                generate_program_payload(name="CAS_Sync_Program")
            )
            program_id = prog_data["id"]
            logger.info(f"Обычная программа: ID={program_id}")

        with allure.step("3. Синхронизировать программу с CAS"):
            result = external_cas_endpoint.sync_program(program_id)
            allure.attach(json.dumps(result, indent=2, ensure_ascii=False), "Синхронизация", allure.attachment_type.JSON)
            logger.info("Программа синхронизирована")

        with allure.step("4. Очистка"):
            ProgramsEndpoint(api_client).mass_delete([program_id])
            omt_cas_endpoint.delete_tenant_org_location(cas_id)