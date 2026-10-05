import allure
import pytest
from utils.logger import logger
from api.helpers.data_generator import get_next_lpd_id
from api.helpers.expectations import expect_status

# БУК и LPD есть только на stage — на других окружениях эти тесты пропускаются (см. conftest, маркер env)
pytestmark = pytest.mark.env("stage")


@allure.feature("LPD API")
@allure.story("Create LPD")
class TestLpdAPI:
    """Тесты на создание LPD."""

    @allure.title("Создание LPD с валидацией ID")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_create_lpd_with_validation(self, lpd_endpoint, created_lpd):
        """Валидация ID → создание LPD."""

        with allure.step("1. Валидировать LPD ID"):
            lpd_id = get_next_lpd_id()
            valid = lpd_endpoint.validate_id(lpd_id)
            assert valid, f"Валидация LPD ID {lpd_id} не прошла"
            logger.info(f"LPD ID {lpd_id} провалидирован")

        with allure.step("2. Создать LPD"):
            lpd = created_lpd(lpd_id=lpd_id)
            assert lpd["id"], "ID не должен быть пустым"
            logger.info(f"LPD создан: ID={lpd['id']}, Name={lpd['name']}")

    @allure.title("Валидация несуществующего LPD ID")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    @pytest.mark.api
    def test_validate_invalid_lpd_id(self, lpd_endpoint):
        """Валидация несуществующего ID."""
        success = lpd_endpoint.validate_id("9999999")
        logger.info(f"Результат валидации: {'✅' if success else '❌'}")

    @allure.title("Создание LPD без названия")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "negative", "validation")
    @pytest.mark.api
    def test_create_lpd_without_name(self, lpd_endpoint, api_client):
        """Попытка создать LPD без названия → 422."""
        from api.helpers.data_generator import generate_lpd_payload

        payload = generate_lpd_payload(lpd_id=get_next_lpd_id())
        payload["data"]["attributes"]["name"] = None

        resp = api_client.post("/content", json=payload)
        allure.attach(str(resp.status_code), "Status code", allure.attachment_type.TEXT)
        allure.attach(resp.text, "Response body", allure.attachment_type.TEXT)

        expect_status(resp, 422)
        logger.info(f"Без названия отклонено: {resp.status_code}")

    @allure.title("Массовое удаление активностей")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "delete")
    @pytest.mark.api
    def test_mass_delete_activities(self, lpd_endpoint, created_lpd):
        """Создать и массово удалить."""

        with allure.step("1. Создать LPD"):
            lpd = created_lpd(lpd_id=get_next_lpd_id())
            logger.info(f"LPD создан: ID={lpd['id']}")

        with allure.step("2. Массово удалить"):
            success = lpd_endpoint.mass_delete([lpd["id"]])
            assert success, "Массовое удаление не прошло"
            logger.info(f"Массово удалён: {lpd['id']}")