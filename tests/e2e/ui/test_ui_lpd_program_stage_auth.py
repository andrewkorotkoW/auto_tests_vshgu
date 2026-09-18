import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from ui.pages.anketa_page import AnketaPage
from utils.logger import logger


@allure.feature("Stage Tests")
@allure.story("UI LPD Program Stage (Auth)")
class TestUILpdProgramStageAuth:

    @allure.title("UI Stage (Program Auth): Создание → Логин → Онбординг → Программа → ЛПД (auth) → Анкета → Отчет")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_ui_lpd_program_auth_flow(self, page, env, program_lpd):
        with allure.step("1-7. Создать программу/поток/модуль, пользователя и авторизованный LPD, назначить"):
            user, lpd, program, stream, module = program_lpd("authorized")

        with allure.step("8. Логин"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            page.screenshot(path="allure-results/stage_ui_prog_auth_01_login.png")
            allure.attach.file("allure-results/stage_ui_prog_auth_01_login.png", "Логин",
                               allure.attachment_type.PNG)

        with allure.step("9-10. Открыть программу, вкладку ЛПД и ЛПД"):
            lpd_page = LpdPage(page)
            lpd_page.open_program_lpd(program["name"], lpd["name"])
            page.screenshot(path="allure-results/stage_ui_prog_auth_02_lpd.png")
            allure.attach.file("allure-results/stage_ui_prog_auth_02_lpd.png", "ЛПД в программе открыт",
                               allure.attachment_type.PNG)

        with allure.step("11-13. Запустить ЛПД, перейти в анкету, пройти её"):
            new_page = lpd_page.launch()
            anketa = AnketaPage(new_page)
            anketa.go()
            anketa.fill_authorized()
            new_page.screenshot(path="allure-results/stage_ui_prog_auth_03_anketa_done.png")
            new_page.close()

        with allure.step("14. Проверить статус «Отчет формируется»"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.wait_report_pending()
            page.screenshot(path="allure-results/stage_ui_prog_auth_04_report_pending.png")
            allure.attach.file("allure-results/stage_ui_prog_auth_04_report_pending.png", "Отчет формируется",
                               allure.attachment_type.PNG)

        logger.info("UI LPD Program Stage (authorized) завершён!")
