import allure
import pytest
from utils.logger import logger


@allure.feature("MIF API")
@allure.story("Set Access")
class TestMifAPI:

    @allure.title("Открыть доступ к MIF")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_set_mif_access(self, created_user, mif_endpoint):
        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Открыть доступ"):
            data = mif_endpoint.set_access([user["id"]], True)
            logger.info(f"Доступ открыт: {data}")

    @allure.title("Закрыть доступ к MIF")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_unset_mif_access(self, created_user, mif_endpoint):
        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Открыть доступ"):
            mif_endpoint.set_access([user["id"]], True)

        with allure.step("3. Закрыть доступ"):
            data = mif_endpoint.set_access([user["id"]], False)
            logger.info(f"Доступ закрыт: {data}")