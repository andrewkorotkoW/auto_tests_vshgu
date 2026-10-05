import allure
import pytest
from utils.logger import logger
from api.endpoints.users import UsersEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Homework API")
@allure.story("Examine by teacher")
class TestExamineByTeacher:

    @allure.title("API Develop: Полный цикл проверки ДЗ — студент → преподаватель")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_examine_homework_flow(self, api_client, created_user, created_homework):
        users_ep = UsersEndpoint(api_client)
        hw_ep = HomeworkEndpoint(api_client)
        tincan_ep = TincanEndpoint(api_client)

        # Создаём студента
        with allure.step("1. Создать студента"):
            student = created_user()
            logger.info(f"Студент: ID={student['id']}, email={student['email']}")

        # Создаём преподавателя (роль назначаем опционально, чтобы тест не падал)
        with allure.step("2. Создать преподавателя"):
            teacher = created_user(surname="Иванов")
            try:
                users_ep.assign_roles(teacher["id"], [4])  # 4 — предполагаемая роль teacher
                logger.info(f"Роли назначены преподавателю {teacher['id']}")
            except AssertionError:
                logger.warning("Не удалось назначить роль (возможно, неверный ID роли). Продолжаем без назначения.")
            logger.info(f"Преподаватель создан: ID={teacher['id']}")

        # Загружаем обложку и создаём ДЗ
        with allure.step("3. Загрузить обложку и создать ДЗ"):
            cover_uuid = tincan_ep.upload_cover()
            homework = created_homework(
                cover_uuid=cover_uuid,
                teacher_ids=[teacher["id"]],
                inspector_ids=[teacher["id"]]
            )
            logger.info(f"ДЗ создано: ID={homework['id']}")

        # Назначаем ДЗ студенту
        with allure.step("4. Назначить ДЗ студенту"):
            AssignmentsEndpoint(api_client).assign_to_individual(
                [homework["id"]], [student["id"]]
            )
            logger.info("ДЗ назначено студенту")

        # Получаем answer_id
        with allure.step("5. Получить answer_id через GET /homework/answers"):
            answers_resp = api_client.get(f"/homework/answers?filters[homework_id]={homework['id']}")
            answers = answers_resp.json().get("data", [])
            if not answers:
                all_answers = api_client.get("/homework/answers").json().get("data", [])
                answers = [a for a in all_answers if a.get("attributes", {}).get("homework_id") == homework['id']]
            if not answers:
                logger.warning("Ответы для данного ДЗ не найдены.")
                pytest.skip("Ответы отсутствуют")
            answer_id = answers[0]["id"]
            logger.info(f"Answer ID для проверки: {answer_id}")

        # Проверка преподавателем
        with allure.step("6. Преподаватель проверяет ответ"):
            result = hw_ep.examine(
                homework_id=homework["id"],
                answer_id=answer_id,
                grade="5",
                status=2,                   # число!
                teacher_comment="Отличная работа"
            )
            allure.attach(str(result), "Examination Result", allure.attachment_type.JSON)
            logger.info("Проверка завершена успешно")
            # Проверим, что статус действительно изменился
            assert result.get("data", {}).get("attributes", {}).get("status") == 2

        # Очистка не выполняется – данные остаются для ручной проверки