import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.aos_page import AosPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User AOS Flow")
class TestUserAosFlow:

    @allure.title("Пользователь проходит АОС полностью")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_user_complete_aos(self, page, api_client, created_user, created_aos, assignments_endpoint):
        """API: создать → назначить → UI: логин → пройти АОС."""

        # ========== API: ПОДГОТОВКА ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: {user['email']} / {user['password']}")

        with allure.step("2. Создать АОС"):
            aos = created_aos()
            logger.info(f"АОС: ID={aos['id']}")

        with allure.step("3. Активировать АОС"):
            from api.endpoints.aos import AosEndpoint
            aos_ep = AosEndpoint(api_client)
            aos_ep.activate(aos["program_id"], aos["stream_id"], aos["id"])
            logger.info("✅ АОС активирован")

        with allure.step("4. Назначить пользователя в поток"):
            assignments_endpoint.assign(
                aos["program_id"], aos["stream_id"], [user["id"]]
            )
            logger.info("✅ Пользователь назначен")

        # ========== UI: ПРОХОЖДЕНИЕ ==========
        with allure.step("5. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])

        with allure.step("6. Начать АОС"):
            aos_page = AosPage(page)
            aos_page.start_aos(aos["program_name"])

        with allure.step("7. Вопрос 1"):
            aos_page.page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            aos_page.answer_first_option()
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("8. Вопрос 2"):
            aos_page.answer_first_option()
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("9. Вопрос 3"):
            aos_page.answer_first_option()
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("10. Вопрос 4 (текст)"):
            aos_page.answer_textarea("Автотест")
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("11. Вопрос 5 (чекбоксы)"):
            aos_page.answer_first_checkboxes(3)
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("12. Вопрос 6"):
            aos_page.answer_first_option()
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("13. Вопрос 7"):
            aos_page.answer_first_option()
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("14. Вопрос 8 (текст)"):
            aos_page.answer_textarea("Автотест_8_вопрос")
            aos_page.click_answer()
            aos_page.click_next()

        with allure.step("15. Вопрос 9"):
            aos_page.page.locator("input[type='radio']").first.check(force=True)
            aos_page.click_answer()

        with allure.step("16. Завершить АОС"):
            aos_page.click_finish()

        with allure.step("17. Скриншот результата"):
            page.screenshot(path="allure-results/03_aos_completed.png")
            allure.attach.file("allure-results/03_aos_completed.png", "АОС пройден", allure.attachment_type.PNG)

        logger.info("✅ АОС пройден!")

        with allure.step("18. Повторный вход — вкладка не отображается после прохождения АОС"):
            page.context.clear_cookies()
            login_page.login(user["email"], user["password"])
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

            # Снова открываем программу
            page.locator(f"span:has-text('{aos['program_name']}')").first.click()
            # Проходим онбординг, если появился
            try:
                for _ in range(10):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=1000):
                        btn.click(force=True)
                    else:
                        break
            except:
                pass

            # Скриншот после входа в программу
            page.screenshot(path="allure-results/04_reopen_program.png")
            allure.attach.file("allure-results/04_reopen_program.png", "Повторный вход в программу",
                               allure.attachment_type.PNG)

            # Проверяем, что вкладки нет
            assert not page.locator("text=Анкета обратной связи").is_visible(timeout=3000), "Вкладка всё ещё видна!"
            logger.info("Вкладка скрыта")