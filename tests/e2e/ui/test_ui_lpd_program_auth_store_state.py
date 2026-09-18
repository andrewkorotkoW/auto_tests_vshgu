import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from ui.pages.anketa_page import AnketaPage
from utils.logger import logger


@allure.feature("Stage Tests")
@allure.story("UI LPD Program Stage (Auth)")
class TestUILpdProgramStageAuthReset:

    @allure.title("UI Stage (Program Auth): Создание → Логин → Программа → ЛПД (auth) → Анкета → store-state → Сброс")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_ui_lpd_program_auth_flow(self, page, env, program_lpd, lpd_endpoint):
        with allure.step("1-7. Создать программу/поток/модуль, пользователя и авторизованный LPD, назначить"):
            user, lpd, program, stream, module = program_lpd("authorized")

        with allure.step("8-10. Логин, открыть программу, вкладку ЛПД и ЛПД"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            lpd_page = LpdPage(page)
            lpd_page.open_program_lpd(program["name"], lpd["name"])

        with allure.step("11-13. Запустить ЛПД, пройти анкету"):
            new_page = lpd_page.launch()
            anketa = AnketaPage(new_page)
            anketa.go()
            anketa.fill_authorized()
            new_page.close()

        with allure.step("14. Проверить статус «Отчет формируется»"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.wait_report_pending()
            page.screenshot(path="allure-results/reset_prog_01_report_pending.png")

        with allure.step("15. Сбросить прогресс (store-state) и проверить кнопку «Начать»"):
            result = lpd_endpoint.get_result(lpd["id"], user["id"])
            invite_id = (
                result.get("invite_id")
                or result.get("attributes", {}).get("invite_id")
                or f"auth:authorized|content_id:{lpd['id']}|assignment:unknown"
            )
            lpd_endpoint.store_state(user["id"], invite_id, state_id=5, jwt_token=env.lpd_jwt_token)

            page.reload()
            lpd_page.wait_start_button()
            page.screenshot(path="allure-results/reset_prog_02_reset_ready.png")
            allure.attach.file("allure-results/reset_prog_02_reset_ready.png",
                               "Прогресс сброшен, можно начать заново", allure.attachment_type.PNG)

        logger.info("UI LPD Program Stage (authorized) завершён!")
