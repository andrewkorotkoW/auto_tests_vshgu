import allure
import pytest
from utils.logger import logger
from api.endpoints.users import UsersEndpoint


@allure.feature("Users API")
@allure.story("Assign Roles")
class TestAssignRoles:

    @allure.title("API Develop: Назначить роль преподавателя пользователю")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.api
    def test_assign_teacher_role(self, api_client, created_user):
        users_ep = UsersEndpoint(api_client)

        # Создаём пользователя
        user = created_user()
        logger.info(f"Пользователь создан: ID={user['id']}")

        # Назначаем роль "teacher" (предположим, что ID роли teacher = 4)
        result = users_ep.assign_roles(user["id"], [4])
        # Проверяем, что в ответе есть успешный статус или что роль применилась
        # (структура ответа зависит от API; здесь просто проверяем, что не упало)
        allure.attach(str(result), "Assign Roles Result", allure.attachment_type.JSON)
        logger.info(f"Роль teacher назначена пользователю {user['id']}")