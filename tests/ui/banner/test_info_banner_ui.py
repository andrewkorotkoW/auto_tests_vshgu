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
    def test_info_banner_toggle_ui(self, page, info_banner_on, prepared_user):
        """API: включить → проверить → выключить → проверить."""

        with allure.step("1. Создать пользователя"):
            user = prepared_user()

        with allure.step("2. Баннер включён через глобальный API (фикстура info_banner_on, выключение гарантировано после теста)"):
            info_banner_endpoint = info_banner_on

        with allure.step("3. Проверка баннера на странице входа"):
            # Плашка на странице входа рисуется по ответу GET /api/v1/info-banner/show —
            # ждём именно его, а не тишину сети.
            with page.expect_response(lambda r: "/info-banner/show" in r.url, timeout=settings.UI_TIMEOUT):
                page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.screenshot(path="allure-results/banner_login_page.png")
            allure.attach.file("allure-results/banner_login_page.png", "Баннер на странице входа", allure.attachment_type.PNG)
            # на странице входа плашка — div.tech-alert, внутри системы — div.tech-banner
            expect(page.locator("div.tech-alert").first).to_be_visible(timeout=10000)

        with allure.step("4. Логин и проверка баннера после входа"):
            login_page = LoginPage(page)
            # handle_onboarding=False: login() иначе зовёт dismiss_popups(), а тот убирает из DOM
            # саму плашку техработ (remove_tech_banner) — предмет этого теста. Пользователь
            # подготовлен через API (prepared_user), анкеты и тура у него нет; на всякий случай
            # закрываем только их, без dismiss_popups.
            login_page.login(user["email"], user["password"], handle_onboarding=False)
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
            # Негативная проверка ниже (count 0) не должна пройти до ответа API баннера.
            with page.expect_response(lambda r: "/info-banner/show" in r.url, timeout=settings.UI_TIMEOUT):
                page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.screenshot(path="allure-results/banner_off_login.png")
            allure.attach.file("allure-results/banner_off_login.png", "Страница входа без баннера", allure.attachment_type.PNG)
            expect(page.locator("div.tech-alert.show")).to_have_count(0, timeout=5000)

        with allure.step("8. Повторный вход и проверка отсутствия баннера"):
            login_page.login(user["email"], user["password"], handle_onboarding=False)
            page.screenshot(path="allure-results/banner_off_after_login.png")
            allure.attach.file("allure-results/banner_off_after_login.png", "После входа без баннера", allure.attachment_type.PNG)
            # именно плашка техработ: другие v-alert (тосты «Подборка обновилась» и т. п.) не в счёт
            expect(page.locator("div.tech-banner")).to_have_count(0, timeout=5000)

        logger.info("Тест info banner завершён!")