import allure
import pytest
from utils.logger import logger
from api.helpers.data_generator import get_next_lpd_id

# БУК и LPD есть только на stage — на других окружениях эти тесты пропускаются (см. conftest, маркер env)
pytestmark = pytest.mark.env("stage")


@allure.feature("Assign Activities API")
@allure.story("Assign activities to users")
class TestAssignActivitiesAPI:
    """Тесты на назначение активностей пользователям."""

    @allure.title("Назначение активности пользователю")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "api", "positive")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_assign_activity_to_user(self, lpd_endpoint, created_lpd, created_user):
        """Создать LPD и пользователя → назначить активность."""

        with allure.step("1. Создать LPD"):
            lpd = created_lpd(lpd_id=get_next_lpd_id())
            logger.info(f"LPD: ID={lpd['id']}")

        with allure.step("2. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: ID={user['id']}")

        with allure.step("3. Назначить активность пользователю"):
            success = lpd_endpoint.assign_activities(
                content_ids=[lpd["id"]], user_ids=[user["id"]]
            )
            assert success, "Не удалось назначить активность"
            logger.info(f"Активность {lpd['id']} назначена пользователю {user['id']}")

    @allure.title("Открепление активности от пользователя")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.api
    def test_detach_activity_from_user(self, lpd_endpoint, created_lpd, created_user):
        """Назначить и открепить активность."""

        with allure.step("1. Создать LPD и пользователя"):
            lpd = created_lpd(lpd_id=get_next_lpd_id())
            user = created_user()
            logger.info(f"LPD: {lpd['id']}, User: {user['id']}")

        with allure.step("2. Назначить активность"):
            lpd_endpoint.assign_activities([lpd["id"]], [user["id"]])

        with allure.step("3. Открепить активность"):
            success = lpd_endpoint.detach_activities([lpd["id"]], [user["id"]])
            assert success, "Не удалось открепить активность"
            logger.info("Активность откреплена")