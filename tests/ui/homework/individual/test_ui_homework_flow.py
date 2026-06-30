import allure
import pytest
import time
from ui.pages.login_page import LoginPage
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Homework UI")
@allure.story("Full Flow: Create → Assign → UI Launch → Submit Answer")
class TestUIHomeworkFlow:

    @allure.title("E2E Develop: Создать ДЗ, назначить, запустить и отправить ответ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_homework_ui_flow(self, page, api_client, created_user, created_homework):
        # Создаём все необходимые объекты в начале, чтобы они были доступны всегда
        tincan_ep = TincanEndpoint(api_client)
        users_ep = UsersEndpoint(api_client)
        hw_ep = HomeworkEndpoint(api_client)

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

        with allure.step("3. Назначить ДЗ студенту"):
            AssignmentsEndpoint(api_client).assign_to_individual(
                [homework["id"]], [student["id"]]
            )
            logger.info("ДЗ назначено студенту")

        # ========== UI: Логин ==========
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

        with allure.step("6. Открыть индивидуальное обучение, закрыть все онбординги и найти поле для ответа"):
            page.locator("text=Индивидуальное обучение").first.click(force=True)
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")

            # Функция для закрытия одного блока онбординга
            def close_onboarding():
                try:
                    start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                    if start_btn.is_visible(timeout=2000):
                        start_btn.click(force=True)
                        page.wait_for_timeout(1000)
                    for _ in range(15):
                        btn = page.locator('[data-qa="onboarding-popup-next"]')
                        if btn.is_visible(timeout=1000):
                            btn.click(force=True)
                            page.wait_for_timeout(300)
                        else:
                            break
                except:
                    pass

            # Закрываем онбординги до пяти раз
            for i in range(5):
                close_onboarding()
                page.wait_for_timeout(1000)
                if not page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение'), [data-qa='onboarding-popup-next']").is_visible(timeout=1000):
                    logger.info(f"Все онбординги закрыты после {i+1} попыток")
                    break

            page.screenshot(path="allure-results/hw_ui_03_after_onboarding.png")
            allure.attach.file("allure-results/hw_ui_03_after_onboarding.png", "После закрытия онбордингов", allure.attachment_type.PNG)

            # Ищем поле для ответа
            text_area = page.locator("textarea.v-field__input:not([readonly])").first
            if text_area.count() == 0:
                text_area = page.locator("textarea:not([readonly])").first
            if text_area.count() == 0:
                text_area = page.locator("input[type='text']").first

            assert text_area.count() > 0, "Поле для ответа не найдено"
            logger.info("Поле для ответа найдено")

            # Проверка статуса "Назначено" перед отправкой
            with allure.step("6.1 Проверить статус 'Назначено'"):
                assert page.locator("text=Назначено").is_visible(timeout=5000), \
                    "Статус 'Назначено' не отображается"
                logger.info("Статус 'Назначено' отображается")
                page.screenshot(path="allure-results/hw_ui_03_status_assigned.png")
                allure.attach.file("allure-results/hw_ui_03_status_assigned.png", "Статус 'Назначено'",
                                   allure.attachment_type.PNG)

        with allure.step("7. Ввести ответ и отправить"):
            # Заполняем поле
            text_area = page.locator("textarea.v-field__input:not([readonly])").first
            text_area.fill("Привет, Игорь! это автотест")
            page.wait_for_timeout(1000)
            logger.info("Ответ введён")

            # Кнопка «Отправить»
            send_btn = page.locator("span[data-v-1b1d34a4]:has-text('Отправить')")
            if send_btn.count() == 0:
                send_btn = page.locator("button:has(span:has-text('Отправить'))").first
            if send_btn.count() == 0:
                send_btn = page.locator("span:has-text('Отправить')").first

            assert send_btn.count() > 0, "Кнопка «Отправить» не найдена"
            send_btn.click(force=True)
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle")

            # Проверка появления изображения собачки
            dog_img = page.locator("img[alt='dog']")
            assert dog_img.is_visible(timeout=10000), "Картинка собачки не появилась"

            page.screenshot(path="allure-results/hw_ui_04_success.png")
            allure.attach.file("allure-results/hw_ui_04_success.png", "Ответ отправлен, собачка показана", allure.attachment_type.PNG)

            # Закрываем модальное окно через JavaScript (Vuetify dialog)
            page.evaluate("""
                () => {
                    // Ищем активный v-dialog и закрываем его
                    const dialog = document.querySelector('.v-dialog--active');
                    if (dialog) {
                        dialog.remove();  // удаляем из DOM
                        return 'dialog-removed';
                    }
                    // Ищем оверлей и кликаем по нему
                    const overlay = document.querySelector('.v-overlay--active');
                    if (overlay) overlay.click();
                    return 'overlay-clicked';
                }
            """)
            page.wait_for_timeout(3000)
            page.screenshot(path="allure-results/hw_ui_05_closed.png")
            allure.attach.file("allure-results/hw_ui_05_closed.png", "Окно закрыто", allure.attachment_type.PNG)
            logger.info("Ответ успешно отправлен, окно закрыто")
            page.screenshot(path="allure-results/hw_ui_05_closed.png")

            # Проверка статуса "Отправлено на проверку" после отправки
            with allure.step("7.1 Проверить статус 'Отправлено на проверку'"):
                assert page.locator("text=Отправлено на проверку").is_visible(timeout=5000), \
                    "Статус 'Отправлено на проверку' не отображается"
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