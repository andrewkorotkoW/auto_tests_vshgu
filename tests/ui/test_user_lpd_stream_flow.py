import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from utils.logger import logger

# БУК и LPD есть только на stage — на других окружениях эти тесты пропускаются (см. conftest, маркер env)
pytestmark = pytest.mark.env("stage")


@allure.feature("UI Tests")
@allure.story("User LPD Flow (Stream)")
class TestUserLpdStreamFlow:

    @allure.title("Пользователь открывает LPD через поток")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_user_open_lpd_stream(self, page, api_client, created_user, created_lpd, lpd_endpoint, assignments_endpoint, created_program, created_stream, created_module):
        """API: программа → поток → модуль → пользователь → LPD → UI: логин → открыть LPD."""

        # ========== API ==========
        with allure.step("1. Создать программу"):
            program = created_program(name="E2E_LPD_Stream_UI")

        with allure.step("2. Создать поток"):
            stream = created_stream(program_id=program["id"])

        with allure.step("3. Создать модуль"):
            module = created_module(program_id=program["id"], stream_id=stream["id"])

        with allure.step("4. Создать пользователя"):
            user = created_user()

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

        with allure.step("6. Создать и назначить LPD"):
            from api.helpers.data_generator import get_next_lpd_id
            lpd = created_lpd(lpd_id=get_next_lpd_id())
            lpd_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [lpd["id"]])
            lpd_endpoint.assign_users(module["id"], lpd["id"], stream["id"], [user["id"]])

        # ========== UI ==========
        with allure.step("7. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/lpd_stream_login.png")
            allure.attach.file("allure-results/lpd_stream_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("8. Открыть LPD через поток"):
            lpd_page = LpdPage(page)
            lpd_page.start_stream_lpd(program["name"])
            page.screenshot(path="allure-results/lpd_stream_open.png")
            allure.attach.file("allure-results/lpd_stream_open.png", "LPD открыт", allure.attachment_type.PNG)

        logger.info("LPD через поток открыт!")