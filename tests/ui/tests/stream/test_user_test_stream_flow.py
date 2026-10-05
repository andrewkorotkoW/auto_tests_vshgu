import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Test Flow (Stream)")
class TestUserTestStreamFlow:

    @allure.title("Пользователь открывает Тест через поток")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_user_open_test_stream(self, page, api_client, created_user, tests_endpoint, assignments_endpoint, created_program, created_stream, created_module):
        """API: программа → поток → модуль → пользователь → Тест → UI: логин → открыть Тест."""

        # ========== API ==========
        with allure.step("1. Создать программу"):
            program = created_program(name="E2E_Test_Stream_UI")

        with allure.step("2. Создать поток"):
            stream = created_stream(program_id=program["id"])

        with allure.step("3. Создать модуль"):
            module = created_module(program_id=program["id"], stream_id=stream["id"])

        with allure.step("4. Создать пользователя"):
            user = created_user()

        with allure.step("5. Назначить пользователя на поток"):
            assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

        with allure.step("6. Создать тест с вопросами и назначить"):
            from api.endpoints.tincan import TincanEndpoint
            from api.helpers.data_generator import generate_test_payload, generate_question_payload

            tincan_ep = TincanEndpoint(api_client)
            cover_uuid = tincan_ep.upload_cover()

            test_data = tests_endpoint.create(generate_test_payload(cover_uuid=cover_uuid))
            test_id = test_data["id"]
            logger.info(f"Тест создан: ID={test_id}, name={test_data['name']}")

            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос #{i}", question_type="single")
                tests_endpoint.create_question(test_id, q)
                logger.info(f"Вопрос #{i} добавлен")

            assignments_endpoint.assign_content_to_module(program["id"], stream["id"], module["id"], [test_id])
            logger.info(f"Тест назначен в модуль {module['id']}")

        # ========== UI ==========
        with allure.step("7. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/test_stream_login.png")
            allure.attach.file("allure-results/test_stream_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("8. Онбординг"):
            # Анкета «данные о себе» + cookie-баннер + тур — закрываем общим хелпером,
            # т.к. анкета блокирует страницу и перехватывает клики (не только тур).
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/test_stream_onboarding.png")
            logger.info("Онбординг пройден")

        with allure.step("9. Открыть программу и пройти онбординг"):
            program_element = page.locator(f"text={program['name']}")
            expect(program_element).to_be_visible(timeout=15000)
            program_element.first.click(force=True)
            logger.info(f"Программа '{program['name']}' открыта")

            # Онбординг внутри программы
            UserSidebarPage(page).pass_onboarding()
            logger.info("Онбординг внутри программы пройден")

        with allure.step("10. Открыть тест"):
            # Тест находится на вкладке «Курсы и тесты», по умолчанию открыта «Расписание».
            # Только что назначенный контент модуля появляется в списке не сразу —
            # ретраим reload, пока не пропадёт задержка индексации.
            tests_tab = page.locator("text=Курсы и тесты").first
            expect(tests_tab).to_be_visible(timeout=15000)
            tests_tab.click(force=True)

            test_element = page.locator(f"text={test_data['name']}")
            found = False
            for attempt in range(4):
                try:
                    expect(test_element).to_be_visible(timeout=10000)
                    found = True
                    break
                except AssertionError:
                    logger.info(f"Тест не найден на вкладке (попытка {attempt + 1}/4), reload+retry")
                    page.wait_for_timeout(5000)
                    page.reload()
                    page.wait_for_load_state("networkidle")
                    UserSidebarPage(page).dismiss_popups()
                    page.locator("text=Курсы и тесты").first.click(force=True)
            assert found, f"Тест '{test_data['name']}' не отображается на вкладке «Курсы и тесты» после 4 попыток"
            test_element.first.click(force=True)

            start_button = page.locator("span:has-text('Начать')").first
            expect(start_button).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/test_stream_open.png")
            logger.info("Тест открыт, кнопка 'Начать' видна")