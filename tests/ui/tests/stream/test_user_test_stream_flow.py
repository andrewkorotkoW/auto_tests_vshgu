import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.test_page import TestPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Test Flow (Stream)")
class TestUserTestStreamFlow:

    @allure.title("Пользователь открывает Тест через поток")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.xfail(
        reason=(
            "Известный дефект стенда develop (тот же класс, что в "
            "tests/ui/homework/individual/test_ui_homework_flow.py и др., но здесь для "
            "назначения через модуль потока): после assignments_endpoint.assign_content_to_module "
            "вкладка «Курсы и тесты» модуля показывает только демо-примеры («Пример "
            "назначенного курса» и т.п.) — назначенный тест не появляется в списке. "
            "Подтверждено скриншотом: вкладка открыта верно, но в списке нет карточки с "
            "реальным именем теста."
        ),
        strict=False,
    )
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
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/test_stream_login.png")
            allure.attach.file("allure-results/test_stream_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("9. Открыть программу и пройти онбординг"):
            test_page = TestPage(page)
            # Тур иногда рендерится с задержкой после networkidle и переживает первый
            # dismiss_popups() — повторный вызов подчищает затемнение, которое иначе прячет
            # реальные карточки программ на «Моё обучение»
            UserSidebarPage(page).dismiss_popups()
            program_element = page.locator(f"text={program['name']}").first
            expect(program_element).to_be_visible(timeout=15000)
            program_element.click(force=True)
            logger.info(f"Программа '{program['name']}' открыта")

            UserSidebarPage(page).dismiss_popups()
            logger.info("Онбординг внутри программы пройден")

        with allure.step("10. Открыть тест"):
            # Тест лежит в модуле на вкладке «Курсы и тесты» — по умолчанию открыта
            # «Расписание» (см. AdminStreamGroupsPage/PracticalTaskPage.open_courses_and_tests_tab)
            courses_tab = page.locator("xpath=//span[normalize-space()='Курсы и тесты']")
            expect(courses_tab).to_be_visible(timeout=15000)
            courses_tab.click(force=True)

            test_element = page.locator(f"text={test_data['name']}").first
            expect(test_element).to_be_visible(timeout=15000)
            test_element.click(force=True)

            start_button = page.locator("span:has-text('Начать')")
            expect(start_button).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/test_stream_open.png")
            logger.info("Тест открыт, кнопка 'Начать' видна")