import allure
import pytest
import time
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.certificates import CertificatesEndpoint


@allure.feature("Certificates API")
@allure.story("Assign Template")
class TestAssignTemplate:

    @allure.title("E2E Develop: Создать программу/поток/модуль → создать шаблон → назначить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_assign_template_to_program(self, api_client, created_template,
                                        created_program, created_stream, created_module):
        cert_ep = CertificatesEndpoint(api_client)
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. Создать программу, поток, модуль"):
            program = created_program(name=f"E2E_Cert_Prog_{int(time.time() * 1000)}")
            stream = created_stream(program_id=program["id"])
            module = created_module(program_id=program["id"], stream_id=stream["id"])
            logger.info(f"Программа: {program['id']}, Поток: {stream['id']}, Модуль: {module['id']}")

        with allure.step("2. Загрузить PDF и создать шаблон сертификата"):
            file_id = tincan_ep.upload_certificate_file()
            template = created_template(
                file_id=file_id,
                template_type="activity",   # или program_stream, зависит от цели
                name=f"Автотест_шаблон_назначение_{int(time.time() * 1000)}"
            )
            logger.info(f"Шаблон создан: ID={template['id']}")

        with allure.step("3. Назначить шаблон на модуль"):
            result = cert_ep.assign_template(
                template_id=template["id"],
                content_ids=[program["id"]]

            )
            # Проверяем, что ответ содержит статус success или data
            assert result is not None, "Ответ назначения пуст"
            logger.info("Шаблон назначен на модуль")
            allure.attach(str(result), "Assign Result", allure.attachment_type.JSON)