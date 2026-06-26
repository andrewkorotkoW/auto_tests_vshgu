import allure
import pytest
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint


@allure.feature("Homework API")
@allure.story("Create Homework")
class TestCreateHomework:

    @allure.title("API Develop: Создать практическое задание с обложкой и преподавателем")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_create_homework_full(self, api_client, created_user, created_homework):
        tincan_ep = TincanEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)

        with allure.step("1. Загрузить обложку"):
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка загружена: {cover_uuid}")

        with allure.step("2. Найти или создать преподавателя с фамилией на 'ов'"):
            # Ищем существующих пользователей с фамилией, оканчивающейся на "ов"
            params = {"filter[surname]": "ов"}
            teachers = users_ep.get_users(params)
            if teachers:
                teacher_id = teachers[0]["id"]
                logger.info(f"Найден существующий преподаватель: ID={teacher_id}, фамилия={teachers[0]['attributes']['surname']}")
            else:
                # Если нет – создаём нового
                user = created_user(surname="Иванов")
                teacher_id = user["id"]
                logger.info(f"Создан новый преподаватель: ID={teacher_id}, фамилия={user['surname']}")

            teacher_ids = [teacher_id]

        with allure.step("3. Создать практическое задание"):
            homework = created_homework(
                cover_uuid=cover_uuid,
                teacher_ids=teacher_ids,
                inspector_ids=teacher_ids
            )

            assert homework["id"] is not None
            assert "Автотест_практическое_задание_админка" in homework["name"]
            assert homework["attributes"]["content_type"] == "homework"

            logger.info(f"Практическое задание создано: ID={homework['id']}, name={homework['name']}")
            allure.attach(str(homework), "Homework", allure.attachment_type.JSON)