import allure
import pytest
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint


@allure.feature("Homework API")
@allure.story("Create Homework (10-point)")
class TestCreateHomeworkTenPoint:

    @allure.title("API Develop: Создать практическое задание (10-балльное) с обложкой и преподавателем")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_create_homework_ten_point(self, api_client, created_user, created_homework_ten_point):
        tincan_ep = TincanEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)

        with allure.step("1. Загрузить обложку"):
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

        with allure.step("2. Найти или создать преподавателя с фамилией на 'ов'"):
            params = {"filter[surname]": "ов"}
            teachers = users_ep.get_users(params)
            if teachers:
                teacher_id = teachers[0]["id"]
                logger.info(f"Найден существующий преподаватель: ID={teacher_id}")
            else:
                user = created_user(surname="Иванов")
                teacher_id = user["id"]
                logger.info(f"Создан новый преподаватель: ID={teacher_id}")

        with allure.step("3. Создать 10‑балльное практическое задание"):
            homework = created_homework_ten_point(
                cover_uuid=cover_uuid,
                teacher_ids=[teacher_id],
                inspector_ids=[teacher_id]
            )

            assert homework["id"] is not None
            assert homework["attributes"]["content_type"] == "homework"
            assert homework["attributes"]["grade_type"] == "ten_point"

            logger.info(f"10‑балльное задание создано: ID={homework['id']}")
            allure.attach(str(homework), "Homework (10-point)", allure.attachment_type.JSON)