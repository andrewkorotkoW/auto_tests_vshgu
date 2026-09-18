import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from ui.pages.anketa_page import AnketaPage
from utils.logger import logger


@allure.feature("Stage Tests")
@allure.story("UI LPD Stage (Auth)")
class TestUILpdStageAuthReset:

    @allure.title("UI Stage (Ind Auth): Создание → Логин → ЛПД (auth) → Анкета → store-state → Сброс")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_ui_lpd_auth_flow(self, page, env, individual_lpd, lpd_endpoint):
        with allure.step("1-3. Создать пользователя и авторизованный LPD, назначить на инд. трек"):
            user, lpd = individual_lpd("authorized")

        with allure.step("4-6. Логин, открыть ЛПД"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            lpd_page = LpdPage(page)
            lpd_page.open_individual_lpd(lpd["name"])

        with allure.step("7-9. Запустить ЛПД, пройти анкету"):
            new_page = lpd_page.launch()
            anketa = AnketaPage(new_page)
            anketa.go()
            anketa.fill_authorized()
            new_page.close()

        with allure.step("10. Проверить статус «Отчет формируется»"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.wait_report_pending()
            page.screenshot(path="allure-results/reset_ind_01_report_pending.png")

        with allure.step("11. Сбросить прогресс (store-state) и проверить кнопку «Начать»"):
            result = lpd_endpoint.get_result(lpd["id"], user["id"])
            invite_id = (
                result.get("invite_id")
                or result.get("attributes", {}).get("invite_id")
                or f"auth:authorized|content_id:{lpd['id']}|assignment:unknown"
            )
            lpd_endpoint.store_state(user["id"], invite_id, state_id=5, jwt_token=env.lpd_jwt_token)

            page.reload()
            lpd_page.wait_start_button()
            page.screenshot(path="allure-results/reset_ind_02_reset_ready.png")
            allure.attach.file("allure-results/reset_ind_02_reset_ready.png",
                               "Прогресс сброшен, можно начать заново", allure.attachment_type.PNG)

        logger.info("UI LPD Stage (authorized, ind track) завершён!")
