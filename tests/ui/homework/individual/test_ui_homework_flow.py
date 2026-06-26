import allure
import pytest
import time
from ui.pages.login_page import LoginPage
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint
from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Homework UI")
@allure.story("Full Flow: Create → Assign → UI Launch → Submit Answer")
class TestUIHomeworkFlow:

    @allure.title("E2E Develop: Создать ДЗ, назначить, запустить и отправить ответ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_homework_ui_flow(self, page, api_client, created_user, created_homework):
        tincan_ep = TincanEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)

        # ========== API: Подготовка данных ==========
        with allure.step("1. Создать студента и преподавателя"):
            student = created_user()
            logger.info(f"Студент: ID={student['id']}, email={student['email']}")

            # Ищем преподавателя с фамилией на «ов»
            params = {"filter[surname]": "ов"}
            teachers = users_ep.get_users(params)
            if teachers:
                teacher_id = teachers[0]["id"]
                logger.info(f"Преподаватель найден: ID={teacher_id}")
            else:
                teacher = created_user(surname="Иванов")
                teacher_id = teacher["id"]
                logger.info(f"Создан преподаватель: ID={teacher_id}")

        with allure.step("2. Загрузить обложку и создать ДЗ"):
            cover_uuid = tincan_ep.upload_cover()
            logger.info(f"Обложка: {cover_uuid}")

            homework = created_homework(
                cover_uuid=cover_uuid,
                teacher_ids=[teacher_id],
                inspector_ids=[teacher_id]
            )
            logger.info(f"ДЗ создано: ID={homework['id']}, name={homework['name']}")

        with allure.step("3. Назначить ДЗ студенту через инд. трек"):
            AssignmentsEndpoint(api_client).assign_to_individual(
                [homework["id"]], [student["id"]]
            )
            logger.info("ДЗ назначено студенту")

        # ========== UI: Логин и поиск ==========
        with allure.step("4. Логин"):
            login_page = LoginPage(page)
            login_page.login(student["email"], student["password"])
            page.wait_for_timeout(3000)
            page.screenshot(path="allure-results/hw_ui_01_login.png")
            allure.attach.file("allure-results/hw_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5. Онбординг"):
            try:
                start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                if start_btn.is_visible(timeout=3000):
                    start_btn.click(force=True)
                    page.wait_for_timeout(1000)
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass
            page.screenshot(path="allure-results/hw_ui_02_onboarding.png")
            allure.attach.file("allure-results/hw_ui_02_onboarding.png", "Онбординг", allure.attachment_type.PNG)

        with allure.step("6. Открыть индивидуальное обучение и запустить задание"):
            page.locator("text=Индивидуальное обучение").first.click(force=True)
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")

            # Закрываем внутренний онбординг
            try:
                start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                if start_btn.is_visible(timeout=3000):
                    start_btn.click(force=True)
                    page.wait_for_timeout(1000)
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass

            # Ждём появления кнопки «Начать»
            page.wait_for_selector("button.v-btn:has(span:has-text('Начать'))", timeout=15000)
            page.screenshot(path="allure-results/hw_ui_03_ready.png")
            allure.attach.file("allure-results/hw_ui_03_ready.png", "Кнопка Начать найдена", allure.attachment_type.PNG)

            # Нажимаем «Начать»
            page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button.v-btn');
                    for (const b of btns) {
                        if (b.textContent.includes('Начать')) { b.click(); break; }
                    }
                }
            """)
            page.wait_for_timeout(3000)

            # Если после «Начать» появляется «Приступить к изучению»
            if page.locator("button.v-btn:has(span:has-text('Приступить к изучению'))").is_visible(timeout=5000):
                page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button.v-btn');
                        for (const b of btns) {
                            if (b.textContent.includes('Приступить к изучению')) { b.click(); break; }
                        }
                    }
                """)
                page.wait_for_timeout(5000)

            page.wait_for_load_state("networkidle")
            page.screenshot(path="allure-results/hw_ui_04_launched.png")
            allure.attach.file("allure-results/hw_ui_04_launched.png", "ДЗ запущено", allure.attachment_type.PNG)
            logger.info("ДЗ успешно запущено")

        with allure.step("7. Ввести ответ и отправить"):
            # Ввод ответа
            text_area = page.locator("textarea.v-field__input")
            assert text_area.count() > 0, "Поле для ответа не найдено"
            text_area.fill("Привет, Игорь! это автотест")
            page.wait_for_timeout(1000)
            logger.info("Ответ введён")

            # Кнопка «Отправить»
            send_btn = page.locator("button.v-btn:has(span:has-text('Отправить'))")
            if send_btn.count() == 0:
                send_btn = page.locator("button:has-text('Отправить')").first
            if send_btn.count() == 0:
                send_btn = page.locator("span:has-text('Отправить')").first

            assert send_btn.count() > 0, "Кнопка «Отправить» не найдена"
            send_btn.click(force=True)
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle")

            # Проверка успешной отправки
            success_msg = page.locator("div:has-text('успешно'), div:has-text('задание сдано'), div:has-text('отправлено')").first
            assert success_msg.is_visible(timeout=10000), "Сообщение об успешной отправке не появилось"

            page.screenshot(path="allure-results/hw_ui_05_sent.png")
            allure.attach.file("allure-results/hw_ui_05_sent.png", "Ответ отправлен", allure.attachment_type.PNG)
            logger.info("Ответ успешно отправлен")

        # ========== Очистка ==========
        with allure.step("8. Очистка данных"):
            AssignmentsEndpoint(api_client).detach_from_individual(
                [homework["id"]], [student["id"]]
            )
            # Используем HomeworkEndpoint для удаления задания
            from api.endpoints.homework import HomeworkEndpoint
            HomeworkEndpoint(api_client).delete(homework["id"])
            try:
                UsersEndpoint(api_client).delete(student["id"])
            except:
                pass
            if not teachers:
                try:
                    UsersEndpoint(api_client).delete(teacher_id)
                except:
                    pass
            logger.info("Очистка завершена")