import allure
import pytest
from utils.logger import logger


@allure.feature("Alpina API")
@allure.story("Set User Status")
class TestAlpinaAPI:

    @allure.title("Открыть доступ к Альпине для пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_set_alpina_status(self, created_user, alpina_endpoint):
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: ID={user['id']}")

        with allure.step("2. Открыть доступ к Альпине"):
            data = alpina_endpoint.set_status([user["id"]], True)
            logger.info(f"Доступ открыт: {data}")

    @allure.title("Закрыть доступ к Альпине")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_unset_alpina_status(self, created_user, alpina_endpoint):
        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Открыть доступ"):
            alpina_endpoint.set_status([user["id"]], True)

        with allure.step("3. Закрыть доступ"):
            data = alpina_endpoint.set_status([user["id"]], False)
            logger.info(f"Доступ закрыт: {data}")