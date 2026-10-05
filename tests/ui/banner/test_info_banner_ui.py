import allure
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Info Banner")
class TestInfoBannerUI:

    @allure.title("Включение/выключение инфо-баннера и проверка на портале")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_info_banner_toggle_ui(self, page, info_banner_on, created_user):
        """API: включить → проверить → выключить → проверить."""

        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Баннер включён через глобальный API (фикстура info_banner_on, выключение гарантировано после теста)"):
            info_banner_endpoint = info_banner_on

        with allure.step("3. Проверка баннера на странице входа"):
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/banner_login_page.png")
            allure.attach.file("allure-results/banner_login_page.png", "Баннер на странице входа", allure.attachment_type.PNG)
            # на странице входа плашка — div.tech-alert, внутри системы — div.tech-banner
            expect(page.locator("div.tech-alert").first).to_be_visible(timeout=10000)

        with allure.step("4. Логин и проверка баннера после входа"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            # Новая анкета «заполните данные о себе» перекрывает страницу и крестик баннера — закрываем только её,
            # dismiss_popups() здесь не подходит: он убирает и саму плашку техработ
            sidebar = UserSidebarPage(page)
            sidebar.dismiss_anketa()
            sidebar.pass_onboarding()  # вводное окно тура лежит поверх страницы и перехватывает клики
            page.screenshot(path="allure-results/banner_after_login.png")
            allure.attach.file("allure-results/banner_after_login.png", "Баннер после входа", allure.attachment_type.PNG)
            banner = page.locator("div.tech-banner").first
            expect(banner).to_be_visible(timeout=10000)

        with allure.step("5. Закрыть баннер по кнопке"):
            banner.locator("button, svg.v-icon__svg").first.click()
            expect(banner).to_be_hidden(timeout=5000)

        with allure.step("6. Выключить баннер через API"):
            info_banner_endpoint.toggle(False)

        with allure.step("7. Проверка на странице входа (баннер выключен)"):
            page.context.clear_cookies()
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/banner_off_login.png")
            allure.attach.file("allure-results/banner_off_login.png", "Страница входа без баннера", allure.attachment_type.PNG)
            expect(page.locator("div.tech-alert.show")).to_have_count(0, timeout=5000)

        with allure.step("8. Повторный вход и проверка отсутствия баннера"):
            login_page.login(user["email"], user["password"])
            page.screenshot(path="allure-results/banner_off_after_login.png")
            allure.attach.file("allure-results/banner_off_after_login.png", "После входа без баннера", allure.attachment_type.PNG)
            # именно плашка техработ: другие v-alert (тосты «Подборка обновилась» и т. п.) не в счёт
            expect(page.locator("div.tech-banner")).to_have_count(0, timeout=5000)

        logger.info("Тест info banner завершён!")