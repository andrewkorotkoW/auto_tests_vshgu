import allure
import pytest
import json
from utils.logger import logger


@allure.feature("OMT CAS API")
@allure.story("Tenant Org Locations")
class TestOmtCasAPI:

    @allure.title("Создание и удаление связи ОМТ КАС")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_tenant_org_location(self, omt_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload

        with allure.step("1. Создать связь"):
            payload = generate_cas_payload()
            allure.attach(json.dumps(payload, indent=2, ensure_ascii=False),
                         "Запрос", allure.attachment_type.JSON)

            data = omt_cas_endpoint.create_tenant_org_location(payload)
            cas_id = data.get("id")

            allure.attach(json.dumps(data, indent=2, ensure_ascii=False),
                         "Ответ", allure.attachment_type.JSON)

            assert data, "Ответ не должен быть пустым"
            logger.info(f"Связь CAS создана: ID={cas_id}")

        with allure.step("2. Удалить связь"):
            if cas_id:
                success = omt_cas_endpoint.delete_tenant_org_location(cas_id)
                assert success, f"Не удалось удалить связь {cas_id}"
                logger.info(f"Связь CAS удалена: ID={cas_id}")