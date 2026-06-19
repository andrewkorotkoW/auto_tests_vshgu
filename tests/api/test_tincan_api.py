import allure
import pytest
from utils.logger import logger


@allure.feature("Tincan API")
@allure.story("Create Tincan")
class TestTincanAPI:

    @allure.title("Создание курса Tincan")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_tincan(self, created_tincan):
        with allure.step("Создать курс Tincan"):
            tincan = created_tincan(
                archive_uuid="3c0f45b7-dee1-4037-935d-6159629206a0",
                cover_uuid="13279d23-7fa5-4bc2-9f09-15ec32dab5de",
                sub_files_uuids=["d363dc3d-d443-4305-a7d3-9fc6034b870a"]
            )
            assert tincan["id"], "ID не должен быть пустым"
            logger.info(f"Курс создан: ID={tincan['id']}, Name={tincan['name']}")

    @allure.title("Создание Tincan без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_create_tincan_without_name(self, tincan_endpoint, api_client):
        from api.helpers.data_generator import generate_tincan_payload
        payload = generate_tincan_payload()
        payload["data"]["attributes"]["name"] = None
        resp = api_client.post("/content", json=payload)
        allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
        allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)
        assert resp.status_code == 422, f"Ожидался 422, получен {resp.status_code}"
        logger.info(f"Без названия отклонено: {resp.status_code}")

    @allure.title("Загрузка архива курса")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "upload")
    @pytest.mark.api
    def test_upload_archive(self, tincan_endpoint):
        with allure.step("Загрузить архив"):
            archive_uuid = tincan_endpoint.upload_archive()
            assert archive_uuid, "UUID архива не получен"
            logger.info(f"Архив: {archive_uuid}")

    @allure.title("Загрузка обложки")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "upload")
    @pytest.mark.api
    def test_upload_cover(self, tincan_endpoint):
        with allure.step("Загрузить обложку"):
            cover_uuid = tincan_endpoint.upload_cover()
            assert cover_uuid, "UUID обложки не получен"
            logger.info(f"Обложка: {cover_uuid}")

    @allure.title("Загрузка доп файла")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "upload")
    @pytest.mark.api
    def test_upload_sub_file(self, tincan_endpoint):
        with allure.step("Загрузить доп файл"):
            sub_uuid = tincan_endpoint.upload_sub_file()
            assert sub_uuid, "UUID файла не получен"
            logger.info(f"Файл: {sub_uuid}")

    @allure.title("Массовое удаление Tincan")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "delete")
    @pytest.mark.api
    def test_mass_delete_tincan(self, tincan_endpoint):
        from api.helpers.data_generator import generate_tincan_payload
        with allure.step("1. Создать курс"):
            payload = generate_tincan_payload(
                archive_uuid="3c0f45b7-dee1-4037-935d-6159629206a0",
                cover_uuid="13279d23-7fa5-4bc2-9f09-15ec32dab5de",
                sub_files_uuids=["d363dc3d-d443-4305-a7d3-9fc6034b870a"]
            )
            data = tincan_endpoint.create(payload)
            logger.info(f"Курс создан: ID={data['id']}")
        with allure.step("2. Массово удалить"):
            success = tincan_endpoint.mass_delete([data["id"]])
            assert success, "Массовое удаление не прошло"
            logger.info(f"Массово удалён: {data['id']}")