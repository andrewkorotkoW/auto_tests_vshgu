import allure
import pytest
from ui.pages.login_page import LoginPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Alpina Flow")
class TestAlpinaFlow:

    @allure.title("Проверка доступности Альпины после назначения и снятия")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_alpina_access(self, page, created_user, alpina_endpoint):
        from config.settings import settings

        login_page = LoginPage(page)

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: {user['email']}")

        with allure.step("2. Открыть доступ к Альпине"):
            alpina_endpoint.set_status([user["id"]], True)
            logger.info("Доступ открыт")

        # ========== UI ==========
        with allure.step("3. Логин и проверка кнопки Альпины"):
            login_page.login(user["email"], user["password"])

            alpina_btn = page.locator("span.nav-item__text:has-text('Альпина')").first
            assert alpina_btn.is_visible(timeout=5000), "Кнопка Альпины не отображается!"
            page.screenshot(path="allure-results/alpina_01_button.png")
            allure.attach.file("allure-results/alpina_01_button.png", "Кнопка Альпины", allure.attachment_type.PNG)

            with page.context.expect_page() as new_page_info:
                alpina_btn.click(force=True)
            alpina_page = new_page_info.value
            alpina_page.wait_for_load_state("networkidle")
            alpina_page.screenshot(path="allure-results/alpina_02_page.png")
            allure.attach.file("allure-results/alpina_02_page.png", "Страница Альпины", allure.attachment_type.PNG)
            alpina_page.close()

        # ========== API ==========
        with allure.step("4. Закрыть доступ к Альпине"):
            alpina_endpoint.set_status([user["id"]], False)
            logger.info("Доступ закрыт")

        # ========== UI ==========
        with allure.step("5. Повторный вход — кнопки Альпины нет"):
            page.context.clear_cookies()
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle")
            login_page.login(user["email"], user["password"])

            alpina_btn = page.locator("span.nav-item__text:has-text('Альпина')").first
            assert not alpina_btn.is_visible(timeout=3000), "Кнопка Альпины всё ещё видна!"
            logger.info("Кнопка Альпины отсутствует")
            page.screenshot(path="allure-results/alpina_03_no_access.png")
            allure.attach.file("allure-results/alpina_03_no_access.png", "Без Альпины", allure.attachment_type.PNG)

        logger.info("Alpina Flow завершён!")