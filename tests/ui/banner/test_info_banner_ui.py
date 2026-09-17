import allure
import pytest
from ui.pages.login_page import LoginPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Info Banner")
class TestInfoBannerUI:

    @allure.title("Включение/выключение инфо-баннера и проверка на портале")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_info_banner_toggle_ui(self, page, info_banner_endpoint, created_user):
        """API: включить → проверить → выключить → проверить."""

        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Включить баннер через глобальный API"):
            info_banner_endpoint.toggle(True)

        with allure.step("3. Проверка баннера на странице входа"):
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/banner_login_page.png")
            allure.attach.file("allure-results/banner_login_page.png", "Баннер на странице входа", allure.attachment_type.PNG)
            banner = page.locator("p.text")
            assert banner.is_visible(timeout=5000), "Баннер не отображается!"

        with allure.step("4. Логин и проверка баннера после входа"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/banner_after_login.png")
            allure.attach.file("allure-results/banner_after_login.png", "Баннер после входа", allure.attachment_type.PNG)
            banner = page.locator("div.v-alert__content")
            assert banner.is_visible(timeout=5000), "Баннер не отображается после входа!"

        with allure.step("5. Закрыть баннер по кнопке"):
            page.locator("svg.v-icon__svg").first.click()
            banner = page.locator("div.v-alert__content")
            assert not banner.is_visible(timeout=3000), "Баннер не скрылся!"

        with allure.step("6. Выключить баннер через API"):
            info_banner_endpoint.toggle(False)

        with allure.step("7. Проверка на странице входа (баннер выключен)"):
            page.context.clear_cookies()
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/banner_off_login.png")
            allure.attach.file("allure-results/banner_off_login.png", "Страница входа без баннера", allure.attachment_type.PNG)
            banner = page.locator("p.text")
            assert not banner.is_visible(timeout=3000), "Баннер всё ещё виден!"

        with allure.step("8. Повторный вход и проверка отсутствия баннера"):
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/banner_off_after_login.png")
            allure.attach.file("allure-results/banner_off_after_login.png", "После входа без баннера", allure.attachment_type.PNG)
            banner = page.locator("div.v-alert__content")
            assert not banner.is_visible(timeout=3000), "Баннер всё ещё виден после входа!"

        logger.info("Тест info banner завершён!")