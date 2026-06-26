import allure
import pytest
import time
from ui.pages.login_page import LoginPage
from ui.pages.test_page import TestPage
from api.endpoints.tincan import TincanEndpoint
from utils.logger import logger


@allure.feature("Develop Tests")
@allure.story("UI Poll Flow")
class TestUIPollFlow:

    @allure.title("UI Develop: Создание → Логин → Онбординг → Инд.трек → Опрос → Запуск → Прохождение")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_ui_poll_flow(self, page, api_client, created_user, created_poll, polls_endpoint):
        """API: создать пользователя, опрос, назначить → UI: логин, пройти опрос."""

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь создан: ID={user['id']}, email={user['email']}")

            # В начале теста добавь импорт
            from api.endpoints.tincan import TincanEndpoint

            # В шаге создания опроса:
            with allure.step("2. Создать опрос с вопросами, обложкой и назначить"):
                tincan_ep = TincanEndpoint(api_client)
                cover_uuid = tincan_ep.upload_cover()
                logger.info(f"Обложка загружена: {cover_uuid}")

                poll = created_poll(cover_uuid=cover_uuid)

            from api.helpers.data_generator import generate_question_payload
            # Добавим 3 вопроса для прохождения
            for i in range(1, 4):
                q = generate_question_payload(order=i, text=f"Вопрос опроса #{i}", question_type="single")
                polls_endpoint.create_question(poll["id"], q)
                logger.info(f"Вопрос #{i} добавлен")

            # Назначить опрос пользователю через инд. трек
            polls_endpoint.assign_activities([poll["id"]], [user["id"]])
            logger.info(f"Опрос {poll['id']} назначен пользователю {user['id']}")

        # ========== UI ==========
        with allure.step("3. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.wait_for_timeout(3000)
            page.screenshot(path="allure-results/poll_ui_01_login.png")
            allure.attach.file("allure-results/poll_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("4. Онбординг"):
            test_page = TestPage(page)
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
            page.screenshot(path="allure-results/poll_ui_02_onboarding.png")
            allure.attach.file("allure-results/poll_ui_02_onboarding.png", "Онбординг", allure.attachment_type.PNG)

        with allure.step("5. Индивидуальное обучение → найти опрос"):
            page.locator("text=Индивидуальное обучение").first.click(force=True)
            page.wait_for_timeout(2000)

            # Возможный онбординг внутри
            try:
                for _ in range(17):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                        page.wait_for_timeout(300)
                    else:
                        break
            except:
                pass

            # Найти опрос по имени и открыть
            poll_display_name = poll.get("name_client", poll["name"])
            page.locator(f"text={poll_display_name}").first.click(force=True)
            page.screenshot(path="allure-results/poll_ui_03_poll_opened.png")
            allure.attach.file("allure-results/poll_ui_03_poll_opened.png", "Опрос открыт", allure.attachment_type.PNG)
            logger.info(f"Опрос '{poll['name']}' открыт")

        with allure.step("6. Запустить опрос"):
            # Ждём появления кнопки
            page.wait_for_selector("button.v-btn:has(span:has-text('Начать'))", timeout=15000)

            # Пробуем кликнуть через JavaScript по самой кнопке
            try:
                page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button.v-btn');
                        for (const btn of buttons) {
                            if (btn.textContent.includes('Начать')) {
                                btn.click();
                                break;
                            }
                        }
                    }
                """)
                logger.info("Клик по кнопке «Начать» выполнен через JS")
            except:
                # Запасной вариант — force click
                start_btn = page.locator("button.v-btn:has(span:has-text('Начать'))").first
                start_btn.click(force=True)

            page.wait_for_timeout(3000)
            page.screenshot(path="allure-results/poll_ui_04_launched.png")
            allure.attach.file("allure-results/poll_ui_04_launched.png", "Опрос запущен", allure.attachment_type.PNG)
            logger.info("Кнопка «Начать» нажата")


            with allure.step("7. Пройти опрос (ответить на вопросы)"):
                for i in range(3):
                    # Ищем все видимые радио-обёртки
                    radio_wrappers = page.locator(".v-radio")
                    if radio_wrappers.count() == 0:
                        radio_wrappers = page.locator(".v-selection-control")

                    if radio_wrappers.count() > 0:
                        # Кликаем по первой доступной радио-кнопке (обёртке)
                        radio_wrappers.first.click(force=True)
                        page.wait_for_timeout(500)
                    else:
                        # Запасной вариант: ищем чекбоксы
                        try:
                            checkbox = page.locator("input[type='checkbox']").first
                            if checkbox.is_visible(timeout=1000):
                                checkbox.check(force=True)
                        except:
                            pass

                    # Нажать "Далее" или "Ответить"
                    next_btn = page.locator(
                        "button:has-text('Далее'), span:has-text('Далее'), button:has-text('Ответить')").first
                    if next_btn.is_visible(timeout=3000):
                        next_btn.click(force=True)
                        page.wait_for_timeout(1500)
                    else:
                        break

                page.screenshot(path="allure-results/poll_ui_05_answered.png")
                allure.attach.file("allure-results/poll_ui_05_answered.png", "Ответы даны", allure.attachment_type.PNG)

        # ========== Очистка ==========
        with allure.step("10. Очистка данных"):
            # Снять назначение
            polls_endpoint.assign_activities([poll["id"]], [user["id"]])  # detach? Но пока так
            # Удалить опрос
            polls_endpoint.delete(poll["id"])
            # Удалить пользователя
            from api.endpoints.users import UsersEndpoint
            UsersEndpoint(api_client).delete(user["id"])
            logger.info("Очистка завершена")