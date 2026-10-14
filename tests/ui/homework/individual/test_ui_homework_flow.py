import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from ui.pages.practical_task_page import PracticalTaskPage
from config.settings import settings
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Homework UI")
@allure.story("Full Flow: Create → Assign → UI Launch → Submit Answer")
class TestUIHomeworkFlow:

    @allure.title("E2E Develop: Создать ДЗ, назначить, запустить и отправить ответ,")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    @pytest.mark.e2e
    def test_homework_ui_flow(self, page, api_client, prepared_user, created_homework):
        # Создаём все необходимые объекты в начале, чтобы они были доступны всегда
        tincan_ep = TincanEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)
        hw_ep = HomeworkEndpoint(api_client)

        # ========== API: Подготовка данных ==========
        with allure.step("1. Создать студента и преподавателя"):
            student = prepared_user()
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

        with allure.step("3. Назначить ДЗ студенту"):
            AssignmentsEndpoint(api_client).assign_to_individual(
                [homework["id"]], [student["id"]]
            )
            logger.info("ДЗ назначено студенту")

        # ========== UI: Логин ==========
        with allure.step("4. Логин"):
            login_page = LoginPage(page)
            login_page.login(student["email"], student["password"])
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/hw_ui_01_login.png")
            allure.attach.file("allure-results/hw_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5. Открыть индивидуальное обучение, карточку ДЗ и найти поле для ответа"):
            practical_task_page = PracticalTaskPage(page)
            # «Индивидуальное обучение» -> /education/personal/schedule (тур раздела) ->
            # вкладка «Курсы и тесты» -> /education/personal/activities, где отображается
            # назначенное ДЗ (карточка ищется по name_client ИЛИ name)
            UserSidebarPage(page).open_individual_tab("Курсы и тесты")
            display_name = homework.get("name_client") or homework["name"]
            practical_task_page.open_practical_task(display_name)

            page.screenshot(path="allure-results/hw_ui_03_after_onboarding.png")
            allure.attach.file("allure-results/hw_ui_03_after_onboarding.png", "После закрытия онбордингов", allure.attachment_type.PNG)

            text_area = practical_task_page.answer_textarea
            expect(text_area).to_be_visible(timeout=settings.UI_TIMEOUT)
            logger.info("Поле для ответа найдено")

            # Проверка статуса "Назначено" перед отправкой
            with allure.step("5.1 Проверить статус 'Назначено'"):
                expect(page.locator("text=Назначено")).to_be_visible(timeout=5000)
                logger.info("Статус 'Назначено' отображается")
                page.screenshot(path="allure-results/hw_ui_03_status_assigned.png")
                allure.attach.file("allure-results/hw_ui_03_status_assigned.png", "Статус 'Назначено'",
                                   allure.attachment_type.PNG)

        with allure.step("7. Ввести ответ и отправить"):
            practical_task_page.fill_answer("Привет, Игорь! это автотест")
            logger.info("Ответ введён")

            practical_task_page.submit()

            # Проверка появления изображения собачки
            dog_img = page.locator("img[alt='dog']")
            expect(dog_img).to_be_visible(timeout=10000)

            page.screenshot(path="allure-results/hw_ui_04_success.png")
            allure.attach.file("allure-results/hw_ui_04_success.png", "Ответ отправлен, собачка показана", allure.attachment_type.PNG)

            # Закрываем модальное окно кнопкой «×» (vs-modal__close-btn) — у этого диалога
            # нет класса .v-dialog--active (только .v-overlay--active + .v-dialog), поэтому
            # клик по оверлею/скриму не закрывает его, нужна именно кнопка закрытия
            close_button = page.locator("button.vs-modal__close-btn").first
            expect(close_button).to_be_visible(timeout=settings.UI_TIMEOUT)
            close_button.click(force=True)
            # Ждём, пока модалка/оверлей действительно исчезнут из DOM
            page.locator(".v-overlay--active").first.wait_for(
                state="hidden", timeout=settings.UI_TIMEOUT
            )
            page.screenshot(path="allure-results/hw_ui_05_closed.png")
            allure.attach.file("allure-results/hw_ui_05_closed.png", "Окно закрыто", allure.attachment_type.PNG)
            logger.info("Ответ успешно отправлен, окно закрыто")
            page.screenshot(path="allure-results/hw_ui_05_closed.png")

            # Проверка статуса "Отправлено на проверку" после отправки
            with allure.step("7.1 Проверить статус 'Отправлено на проверку'"):
                expect(page.locator("text=Отправлено на проверку")).to_be_visible(timeout=5000)
                logger.info("Статус 'Отправлено на проверку' отображается")
                page.screenshot(path="allure-results/hw_ui_05_status_submitted.png")
                allure.attach.file("allure-results/hw_ui_05_status_submitted.png", "Статус 'Отправлено на проверку'",
                                   allure.attachment_type.PNG)

        # ========== Очистка ==========
        with allure.step("8. Очистка данных"):
            AssignmentsEndpoint(api_client).detach_from_individual(
                [homework["id"]], [student["id"]]
            )
            # Используем HomeworkEndpoint для удаления задания
            hw_ep.delete(homework["id"])
            try:
                users_ep.delete(student["id"])
            except:
                pass
            # Удаляем преподавателя, если он был создан (а не найден)
            if not teachers:
                try:
                    users_ep.delete(teacher_id)
                except:
                    pass
            logger.info("Очистка завершена")