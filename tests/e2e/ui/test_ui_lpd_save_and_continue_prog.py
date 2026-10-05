import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.lpd_page import LpdPage
from ui.pages.anketa_page import AnketaPage
from utils.logger import logger


@allure.feature("Stage Tests")
@allure.story("Продолжить тест ЛПД (Программа)")
class TestUILpdSaveAndContinueProg:

    @allure.title("UI Stage (Программа): Сохранить → Выйти → Войти → Продолжить → Завершить")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.stage
    @pytest.mark.env("stage")
    def test_ui_lpd_save_and_continue_prog(self, page, env, program_lpd):
        with allure.step("1-7. Создать программу/поток/модуль, пользователя и авторизованный LPD, назначить"):
            user, lpd, program, stream, module = program_lpd("authorized")

        with allure.step("8. Логин и открыть ЛПД в программе"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            lpd_page = LpdPage(page)
            lpd_page.open_program_lpd(program["name"], lpd["name"])

        with allure.step("9. Запустить ЛПД → заполнить первую часть анкеты → сохранить"):
            new_page = lpd_page.launch()
            anketa = AnketaPage(new_page)
            anketa.go()
            anketa.fill_authorized(save_only=True)
            new_page.screenshot(path="allure-results/save_prog_01_saved.png")
            new_page.close()

        with allure.step("10. Обновить страницу, открыть ЛПД заново и продолжить"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.open_program_lpd(program["name"], lpd["name"])
            new_page2 = lpd_page.launch(button_text="Продолжить")
            anketa2 = AnketaPage(new_page2)
            anketa2.go()
            anketa2.continue_authorized()
            new_page2.screenshot(path="allure-results/save_prog_02_completed.png")
            new_page2.close()

        with allure.step("11. Проверить статус «Отчет формируется»"):
            page.bring_to_front()
            page.reload()
            lpd_page.complete_program_onboarding()
            lpd_page.wait_report_pending()
            page.screenshot(path="allure-results/save_prog_03_report_pending.png")
            allure.attach.file("allure-results/save_prog_03_report_pending.png", "Отчет формируется",
                               allure.attachment_type.PNG)

        logger.info("UI LPD Save & Continue (Program) завершён!")
