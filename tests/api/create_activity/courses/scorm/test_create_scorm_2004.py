import allure
import pytest
import time
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint


@allure.feature("Courses API")
@allure.story("Create SCORM 2004 Course")
class TestCreateScorm2004:

    @allure.title("API Develop: Создать SCORM 2004 курс с обложкой и архивом")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_create_scorm_2004(self, api_client):
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. Загрузить обложку"):
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

        with allure.step("2. Загрузить архив SCORM"):
            archive_uuid = tincan_ep.upload_archive("test_data/test_lms_scorm_2004.zip")
            logger.info(f"Архив загружен: {archive_uuid}")

        with allure.step("3. Создать SCORM-курс"):
            from api.helpers.data_generator import generate_scorm_payload
            ts = int(time.time() * 1000)
            payload = generate_scorm_payload(
                name=f"Автотест_SCORM2004_{ts}",
                archive_uuid=archive_uuid,
                cover_uuid=cover_uuid
            )
            data = tincan_ep.create(payload)
            assert data is not None
            assert data["id"] is not None
            logger.info(f"SCORM курс создан: ID={data['id']}, name={data['attributes']['name']}")

            allure.attach(str(data), "SCORM Course", allure.attachment_type.JSON)

        with allure.step("4. Очистка (удалить курс)"):
            tincan_ep.mass_delete([data["id"]])
            logger.info("Курс удалён")