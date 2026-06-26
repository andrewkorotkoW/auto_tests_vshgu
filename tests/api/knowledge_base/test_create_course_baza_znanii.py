import allure
import pytest
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint

@allure.feature("Knowledge Base API")
@allure.story("Create Course from Tincan and Toggle Visibility")
class TestCourseMaterial:

    @allure.title("API Develop: Загрузить Tincan-курс → создать материал в БЗ → переключить видимость")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_create_course_material_full_cycle(self, api_client, knowledge_base_endpoint, created_material):
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. Загрузить обложку и архив"):
            cover_uuid = tincan_ep.upload_cover()
            archive_uuid = tincan_ep.upload_archive()
            sub_uuid = tincan_ep.upload_sub_file()  # если нужен sub_file
            logger.info(f"Обложка: {cover_uuid}, архив: {archive_uuid}, sub: {sub_uuid}")

        with allure.step("2. Создать курс Tincan"):
            from api.helpers.data_generator import generate_tincan_payload
            tincan_payload = generate_tincan_payload(
                archive_uuid=archive_uuid,
                cover_uuid=cover_uuid,
                sub_files_uuids=[sub_uuid]
            )
            tincan_data = tincan_ep.create(tincan_payload)
            content_id = tincan_data["id"]
            logger.info(f"Курс Tincan создан, content_id={content_id}")

        with allure.step("3. Создать материал в базе знаний, привязанный к курсу"):
            material = created_material(
                content_id=content_id,
                cover_uuid=cover_uuid,
                authors=[{"name": "AQA", "avatar_url": "", "avatar_uuid": ""}]
            )
            assert material["id"] is not None
            assert material["attributes"]["type"] == "course"
            logger.info(f"Материал создан: ID={material['id']}")

        with allure.step("4. Переключить видимость материала"):
            updated = knowledge_base_endpoint.toggle_visibility(material["id"], is_visible=False)
            assert updated.get("is_visible") == False
            logger.info("Видимость переключена на false")

        allure.attach(str(content_id), "Tincan Content ID", allure.attachment_type.TEXT)
        allure.attach(str(material["id"]), "Material ID", allure.attachment_type.TEXT)

        # 5. Переключить видимость обратно в true
        updated_back = knowledge_base_endpoint.toggle_visibility(material["id"], is_visible=True)
        assert updated_back.get("is_visible") == True
        logger.info("Видимость переключена обратно на true")

        # ========== Очистка ==========
        with allure.step("Очистка данных"):
            # Сначала удаляем материал
            knowledge_base_endpoint.delete_materials([material["id"]])
            # Потом удаляем курс
            tincan_ep.delete(content_id)
            logger.info("Очистка завершена")