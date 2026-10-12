import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from api.endpoints.tincan import TincanEndpoint
from config.settings import settings
from utils.logger import logger


@allure.feature("Develop Tests")
@allure.story("UI Poll Flow")
class TestUIPollFlow:

    @allure.title("UI Develop: Создание → Логин → Онбординг → Инд.трек → Опрос → Запуск → Прохождение")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_ui_poll_flow(self, page, api_client, prepared_user, created_poll, polls_endpoint):
        """API: создать пользователя, опрос, назначить → UI: логин, пройти опрос."""

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = prepared_user()
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
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/poll_ui_01_login.png")
            allure.attach.file("allure-results/poll_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("4. Индивидуальное обучение → найти опрос"):
            # «Индивидуальное обучение» -> тур раздела -> вкладка «Курсы и тесты», где
            # отображается назначенный опрос (карточка ищется по name_client ИЛИ name)
            UserSidebarPage(page).open_individual_tab("Курсы и тесты")

            # Найти опрос по имени и открыть
            poll_display_name = poll.get("name_client") or poll["name"]
            poll_card = page.locator(f"text={poll_display_name}").first
            expect(poll_card).to_be_visible(timeout=30000)
            poll_card.click(force=True)
            page.screenshot(path="allure-results/poll_ui_03_poll_opened.png")
            allure.attach.file("allure-results/poll_ui_03_poll_opened.png", "Опрос открыт", allure.attachment_type.PNG)
            logger.info(f"Опрос '{poll['name']}' открыт")

        with allure.step("6. Запустить опрос — открывается плеер в новой вкладке"):
            # Клик по «Начать» на карточке открывает плеер опроса в новой вкладке
            # (в отличие от homework/proctoring, которые остаются в той же вкладке)
            page.wait_for_selector("button.v-btn:has(span:has-text('Начать'))", timeout=15000)
            with page.context.expect_page(timeout=15000) as new_page_info:
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
            poll_page = new_page_info.value
            poll_page.wait_for_load_state("networkidle")
            logger.info(f"Плеер опроса открыт в новой вкладке: {poll_page.url}")

            # Вступительный слайд плеера — отдельная кнопка «Начать» (реальный клик,
            # не force/JS: force-клик по ней не запускает переход к первому вопросу)
            intro_start = poll_page.locator("button:has-text('Начать')").first
            expect(intro_start).to_be_visible(timeout=15000)
            intro_start.click(timeout=10000)
            expect(intro_start).to_be_hidden(timeout=15000)
            poll_page.screenshot(path="allure-results/poll_ui_04_launched.png")
            allure.attach.file("allure-results/poll_ui_04_launched.png", "Опрос запущен", allure.attachment_type.PNG)
            logger.info("Вступительный слайд пройден")

            with allure.step("7. Пройти опрос (ответить на вопросы)"):
                for i in range(3):
                    radio_wrappers = poll_page.locator(".v-selection-control")
                    if radio_wrappers.count() == 0:
                        break
                    radio_wrappers.first.click(timeout=5000)

                    answer_btn = poll_page.locator("button:has-text('Ответить')").first
                    if answer_btn.count() > 0:
                        answer_btn.click(timeout=5000)

                    next_btn = poll_page.locator("button:has-text('Далее')").first
                    if next_btn.count() > 0 and next_btn.is_visible(timeout=2000):
                        next_btn.click(timeout=5000)
                    poll_page.wait_for_timeout(1000)

                poll_page.screenshot(path="allure-results/poll_ui_05_answered.png")
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