import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger
from api.endpoints.tests import TestsEndpoint
from api.endpoints.users import UsersEndpoint
from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Proctoring UI")
@allure.story("Full Flow: Create → Assign → UI Launch and Pass")
class TestUIProctoringFlow:

    @allure.title("E2E Develop: Создать тест с прокторингом, назначить и пройти в UI")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_proctoring_ui_flow(self, page, api_client, prepared_user, created_test):
        tests_ep = TestsEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)

        # ========== API: Подготовка данных ==========
        with allure.step("1. Создать пользователя"):
            student = prepared_user()
            logger.info(f"Студент: ID={student['id']}, email={student['email']}")

        with allure.step("2. Создать тест с прокторингом и назначить"):
            test = created_test()
            logger.info(f"Тест создан: ID={test['id']}, name={test['name']}")

            from api.helpers.data_generator import generate_question_payload
            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос прокторинга #{i}", question_type="single")
                tests_ep.create_question(test["id"], q)
                logger.info(f"Вопрос #{i} добавлен")

            from api.helpers.data_generator import generate_test_update_proctoring_payload
            proctoring_payload = generate_test_update_proctoring_payload(
                content_id=test["id"],
                name=test["name"],
                is_active=True
            )
            tests_ep.update(test["id"], proctoring_payload)
            logger.info(f"Прокторинг активирован для теста ID={test['id']}")

            AssignmentsEndpoint(api_client).assign_to_individual(
                [test["id"]], [student["id"]]
            )
            logger.info("Тест назначен студенту")

        # ========== UI ==========
        with allure.step("3. Логин"):
            login_page = LoginPage(page)
            login_page.login(student["email"], student["password"])
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/proctoring_ui_01_login.png")
            allure.attach.file("allure-results/proctoring_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("4. Открыть индивидуальное обучение, найти тест и открыть карточку"):
            # «Индивидуальное обучение» -> тур раздела -> вкладка «Курсы и тесты», где
            # отображается назначенный тест (карточка ищется по name_client ИЛИ name)
            UserSidebarPage(page).open_individual_tab("Курсы и тесты")

            display_name = test.get("name_client") or test["name"]
            task_element = page.locator(f"text={display_name}").first
            if task_element.count() == 0:
                task_element = page.locator(f"span.library-card__name:has-text('{display_name}')").first
            expect(task_element).to_be_visible(timeout=30000)
            logger.info(f"Тест '{display_name}' найден")
            task_element.click(force=True)

            # Ждём кнопку «Начать»
            start_button = page.locator("button.v-btn:has(span:has-text('Начать'))")
            expect(start_button).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/proctoring_ui_03_ready.png")
            allure.attach.file("allure-results/proctoring_ui_03_ready.png", "Кнопка Начать найдена", allure.attachment_type.PNG)

        with allure.step("5. Начать тест — открывается тестовая среда прокторинга (Mock Examus)"):
            # На develop прокторинг подключён к тестовой заглушке (Mock Examus,
            # /api/mock-examus/start/), которая открывается в той же вкладке (не в
            # новой) и не содержит реальных вопросов — только кнопку завершения.
            # Разведка 13.10.2026: заглушка держит плеер портала в iframe, и именно плеер,
            # загружаясь, регистрирует попытку — GET /assignments/{uuid}/contents/{id}/launch
            # (201), затем /tests/try/{try_id}/intro. Кнопка «Завершить тест» видна раньше,
            # чем эта цепочка отработает, а сама по себе никакого запроса не порождает —
            # уйдя со страницы до launch, тест в шаге 7 не находил попытки («Попытка» не
            # появлялась). Раньше это прикрывал networkidle (~3.5 с); ждём сам ответ intro —
            # последний запрос загрузки плеера.
            with page.expect_response(
                lambda r: "/tests/try/" in r.url and r.url.endswith("/intro"), timeout=60000
            ):
                page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button.v-btn');
                        for (const b of btns) {
                            if (b.textContent.includes('Начать')) { b.click(); break; }
                        }
                    }
                """)
            finish_btn = page.locator("text=Завершить тест").first
            expect(finish_btn).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/proctoring_ui_04_mock_examus.png")
            allure.attach.file("allure-results/proctoring_ui_04_mock_examus.png", "Тестовая среда Mock Examus", allure.attachment_type.PNG)
            logger.info(f"Тестовая среда прокторинга открыта: {page.url}")

        with allure.step("6. Завершить тест в тестовой среде"):
            finish_btn.click(force=True)
            page.screenshot(path="allure-results/proctoring_ui_05_finished.png")
            allure.attach.file("allure-results/proctoring_ui_05_finished.png", "Тест завершён", allure.attachment_type.PNG)

        with allure.step("7. Проверить, что попытка зафиксирована"):
            shell = UserSidebarPage(page)
            shell.open_individual_tab("Курсы и тесты")
            page.locator(f"text={display_name}").first.click(force=True)
            shell.wait_loaded()
            attempt = page.locator("text=Попытка").first
            expect(attempt).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/proctoring_ui_06_result.png")
            allure.attach.file("allure-results/proctoring_ui_06_result.png", "Результат попытки", allure.attachment_type.PNG)
            logger.info("Попытка прохождения теста зафиксирована")

        # ========== Очистка ==========
        with allure.step("9. Очистка данных"):
            AssignmentsEndpoint(api_client).detach_from_individual(
                [test["id"]], [student["id"]]
            )
            tests_ep.delete(test["id"])
            try:
                UsersEndpoint(api_client).delete(student["id"])
            except:
                pass
            logger.info("Очистка завершена")