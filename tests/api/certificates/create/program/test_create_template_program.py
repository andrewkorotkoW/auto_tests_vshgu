import allure
import pytest
import time
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint


@allure.feature("Certificates API")
@allure.story("Create Program Template")
class TestCreateProgramTemplate:

    @allure.title("API Develop: Создать шаблон сертификата для программы")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_create_program_template(self, api_client, created_template):
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. Загрузить файл сертификата"):
            file_id = tincan_ep.upload_certificate_file()
            assert file_id, "Файл не загрузился, file_id пустой"
            logger.info(f"Файл загружен: {file_id}")

        with allure.step("2. Создать шаблон программы"):
            ts = int(time.time() * 1000)
            template = created_template(
                file_id=file_id,
                template_type="program_stream",
                name=f"Автотест_шаблон_программа_{ts}",
                serial_prefix=str(ts)[-6:]   # последние 6 цифр, макс. длина 6
            )

            assert template["id"] is not None
            assert template["type"] == "program_stream"
            assert template["name"] == f"Автотест_шаблон_программа_{ts}"

            logger.info(f"Шаблон программы создан: ID={template['id']}, name={template['name']}")
            allure.attach(str(template), "Program Template", allure.attachment_type.JSON)