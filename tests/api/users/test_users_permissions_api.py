import allure
import pytest
from utils.logger import logger
from api.client import ApiClient
from api.helpers.expectations import expect_status
from api.helpers.data_generator import generate_user_payload
from config.environments import login, LoginError


@allure.feature("Users API")
@allure.story("Permissions")
class TestUsersPermissionsAPI:
    """Негативные кейсы на доступ: действия админ-API от имени обычного пользователя."""

    @allure.title("Обычный пользователь не может создать другого пользователя через API")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "permissions")
    @pytest.mark.api
    def test_create_user_forbidden_for_regular_user(self, env, created_user):
        """Создаём обычного пользователя (без админских ролей), логинимся под ним
        по email/паролю, которые вернула фикстура created_user, и пытаемся выполнить
        от его имени админское действие POST /users — ожидаем отказ в доступе (403)."""

        with allure.step("1. Создать обычного пользователя от имени администратора"):
            regular_user = created_user()
            logger.info(f"Обычный пользователь создан: ID={regular_user['id']}")

        with allure.step("2. Залогиниться под этим пользователем"):
            try:
                user_session = login(env, regular_user["email"], regular_user["password"])
            except LoginError as exc:
                pytest.skip(f"Не удалось залогиниться под обычным пользователем: {exc}")

        with allure.step("3. Попытаться создать пользователя от его имени"):
            regular_client = ApiClient(
                session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name
            )
            payload = generate_user_payload()
            resp = regular_client.post("/users", json=payload)

            allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
            allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

            expect_status(resp, 403)
            logger.info(f"✓ Действие без прав отклонено: статус {resp.status_code}")
