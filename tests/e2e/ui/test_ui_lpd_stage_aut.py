import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from ui.pages.anketa_page import AnketaPage
from utils.logger import logger


@allure.feature("Stage Tests")
@allure.story("UI LPD Stage (Auth)")
class TestUILpdStageAuth:

    @allure.title("UI Stage: Создание → Логин → Онбординг → Инд.трек → ЛПД (auth) → Анкета → Отчет")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_ui_lpd_auth_flow(self, page, env, individual_lpd):
        with allure.step("1-3. Создать пользователя и авторизованный LPD, назначить на инд. трек"):
            user, lpd = individual_lpd("authorized")

        with allure.step("4. Логин"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            page.screenshot(path="allure-results/stage_ui_auth_01_login.png")
            allure.attach.file("allure-results/stage_ui_auth_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5-6. Индивидуальное обучение → вкладка ЛПД → открыть"):
            lpd_page = LpdPage(page)
            lpd_page.open_individual_lpd(lpd["name"])
            page.screenshot(path="allure-results/stage_ui_auth_02_lpd.png")
            allure.attach.file("allure-results/stage_ui_auth_02_lpd.png", "ЛПД открыт", allure.attachment_type.PNG)

        with allure.step("7-9. Запустить ЛПД, перейти в анкету, пройти её"):
            new_page = lpd_page.launch()
            anketa = AnketaPage(new_page)
            anketa.go()
            anketa.fill_authorized()
            new_page.screenshot(path="allure-results/stage_ui_auth_03_anketa_done.png")
            new_page.close()

        with allure.step("10. Проверить статус «Отчет формируется»"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.wait_report_pending()
            page.screenshot(path="allure-results/stage_ui_auth_04_report_pending.png")
            allure.attach.file("allure-results/stage_ui_auth_04_report_pending.png", "Отчет формируется",
                               allure.attachment_type.PNG)

        logger.info("UI LPD Stage (authorized) завершён!")
