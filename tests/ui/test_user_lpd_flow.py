import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from utils.logger import logger

# БУК и LPD есть только на stage — на других окружениях эти тесты пропускаются (см. conftest, маркер env)
pytestmark = pytest.mark.env("stage")


@allure.feature("UI Tests")
@allure.story("User LPD Flow (Individual)")
class TestUserLpdFlow:

    @allure.title("Пользователь открывает LPD через индивидуальный трек")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_user_open_lpd(self, page, api_client, created_user, created_lpd, lpd_endpoint):
        """API: создать пользователя и LPD → UI: логин → открыть LPD."""

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Создать и назначить LPD"):
            from api.helpers.data_generator import get_next_lpd_id
            lpd = created_lpd(lpd_id=get_next_lpd_id())
            lpd_endpoint.assign_activities([lpd["id"]], [user["id"]])

        # ========== UI ==========
        with allure.step("3. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/lpd_login.png")
            allure.attach.file("allure-results/lpd_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("4. Открыть LPD через инд. трек"):
            lpd_page = LpdPage(page)
            lpd_page.start_lpd()
            page.screenshot(path="allure-results/lpd_open.png")
            allure.attach.file("allure-results/lpd_open.png", "LPD открыт", allure.attachment_type.PNG)

        logger.info("LPD открыт!")