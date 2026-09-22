import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from ui.pages.practical_task_page import PracticalTaskPage
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
    @pytest.mark.xfail(
        reason=(
            "Известный дефект стенда develop (тот же класс, что в "
            "tests/ui/practical_tasks/personal_assignment/test_complete_and_review_personal_assignment.py "
            "и tests/ui/homework/individual/test_ui_homework_flow.py): после API-назначения "
            "(assignments.assign_to_individual, ответ 200) раздел «Индивидуальное обучение» "
            "слушателя не показывает назначенный тест — карточка с его именем не появляется "
            "в UI."
        ),
        strict=False,
    )
    def test_proctoring_ui_flow(self, page, api_client, created_user, created_test):
        tests_ep = TestsEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)

        # ========== API: Подготовка данных ==========
        with allure.step("1. Создать пользователя"):
            student = created_user()
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

        with allure.step("4. Открыть индивидуальное обучение, найти тест и запустить в новой вкладке"):
            practical_task_page = PracticalTaskPage(page)
            practical_task_page.open_individual_education()
            # Тур показывается отдельно на каждой странице (см. докстринг dismiss_popups) —
            # без повторного вызова затемнение перехватывает клик по карточке теста
            UserSidebarPage(page).dismiss_popups()

            # Ищем название теста (внешнее имя)
            display_name = test.get("name_client", test["name"])
            task_element = page.locator(f"text={display_name}").first
            if task_element.count() == 0:
                task_element = page.locator(f"span.library-card__name:has-text('{display_name}')").first
            expect(task_element).to_be_visible(timeout=30000)
            logger.info(f"Тест '{display_name}' найден")

            # Ждём кнопку «Начать»
            start_button = page.locator("button.v-btn:has(span:has-text('Начать'))")
            expect(start_button).to_be_visible(timeout=15000)
            page.screenshot(path="allure-results/proctoring_ui_03_ready.png")
            allure.attach.file("allure-results/proctoring_ui_03_ready.png", "Кнопка Начать найдена", allure.attachment_type.PNG)

            # --- КЛИК С ПЕРЕХВАТОМ НОВОЙ ВКЛАДКИ ---
            with page.context.expect_page(timeout=15000) as new_page_info:
                page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button.v-btn');
                        for (const b of btns) {
                            if (b.textContent.includes('Начать')) { b.click(); break; }
                        }
                    }
                """)

            # Переключаемся на новую вкладку
            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            new_page.screenshot(path="allure-results/proctoring_ui_04_new_tab.png")
            allure.attach.file("allure-results/proctoring_ui_04_new_tab.png", "Новая вкладка с тестом", allure.attachment_type.PNG)
            logger.info(f"Новая вкладка открыта: {new_page.url}")

        # Все дальнейшие шаги выполняем на new_page
        with allure.step("6. Пройти тест (ответить на вопросы)"):
            for i in range(3):
                radio = new_page.locator(".v-radio").first
                if radio.count() == 0:
                    radio = new_page.locator("input[type='radio']").first
                if radio.count() > 0:
                    radio.click(force=True)

                next_btn = new_page.locator("button.v-btn:has(span:has-text('Следующий вопрос'))").first
                if next_btn.count() == 0:
                    next_btn = new_page.locator("span.v-btn__content:has-text('Следующий вопрос')").first
                if next_btn.is_visible(timeout=5000):
                    next_btn.click(force=True)
                else:
                    break

            new_page.screenshot(path="allure-results/proctoring_ui_05_answered.png")
            allure.attach.file("allure-results/proctoring_ui_05_answered.png", "Ответы даны", allure.attachment_type.PNG)

        with allure.step("7. Завершить тест"):
            finish_btn = new_page.locator("button.v-btn:has(span.v-btn__content:has-text('Завершить'))").first
            if finish_btn.count() == 0:
                finish_btn = new_page.locator("span.v-btn__content:has-text('Завершить')").first
            if finish_btn.is_visible(timeout=5000):
                finish_btn.click(force=True)
                new_page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            new_page.screenshot(path="allure-results/proctoring_ui_06_finished.png")
            allure.attach.file("allure-results/proctoring_ui_06_finished.png", "Тест завершён", allure.attachment_type.PNG)

        with allure.step("8. Проверить успешное завершение"):
            success = new_page.locator("div:has-text('успешно'), div:has-text('завершено'), div:has-text('тест пройден')").first
            expect(success).to_be_visible(timeout=10000)
            new_page.screenshot(path="allure-results/proctoring_ui_07_success.png")
            allure.attach.file("allure-results/proctoring_ui_07_success.png", "Тест пройден", allure.attachment_type.PNG)
            logger.info("Тест успешно пройден!")

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