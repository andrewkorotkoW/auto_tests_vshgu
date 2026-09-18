import allure
import pytest
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("Assignments API")
@allure.story("Assign user to stream")
class TestAssignmentsAPI:
    """Тесты на назначение пользователей в поток."""

    @allure.title("Назначение пользователя в поток")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_assign_user_to_stream(self, assigned_user):
        """Назначить пользователя в поток."""

        with allure.step("1. Назначить пользователя"):
            result = assigned_user()

        with allure.step("2. Проверить данные"):
            assert result["user"]["id"], "User ID должен быть"
            assert result["stream"]["id"], "Stream ID должен быть"
            logger.info(f"✓ Пользователь {result['user']['id']} назначен в поток {result['stream']['id']}")

        allure.attach(str(result), name="assignment", attachment_type=allure.attachment_type.JSON)

    @allure.title("Повторное назначение того же пользователя")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_assign_user_twice(self, created_user, created_stream, assignments_endpoint, api_client):
        """Назначить пользователя дважды — система должна обработать без ошибок."""

        with allure.step("1. Создать пользователя и поток"):
            user = created_user()
            stream = created_stream()
            logger.info(f"Пользователь: ID={user['id']}, Поток: ID={stream['id']}")

        with allure.step("2. Назначить первый раз"):
            assignments_endpoint.assign(stream["program_id"], stream["id"], [user["id"]])
            logger.info("✓ Первое назначение успешно")

        with allure.step("3. Назначить повторно"):
            resp = api_client.post(
                f"/programs/{stream['program_id']}/streams/{stream['id']}/assignments",
                json={"data": {"attributes": {"users_ids": [user["id"]]}}}
            )
            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 400)

            logger.info(f"✓ Повторное назначение: статус {resp.status_code}")