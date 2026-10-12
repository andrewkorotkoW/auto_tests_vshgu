import allure
import pytest
from playwright.sync_api import expect

from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Cookie Banner")
class TestUserCookieBanner:

    @allure.title("Пользователь: логин → анкета и онбординг → cookie-баннер → ссылка «Политикой» → «Принимаю» → баннер не повторяется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_user_cookie_banner(self, page, env, created_user):
        """Ожидаемое поведение (владелец, 23.09.2026): баннер показывается после входа в систему,
        на странице входа его нет. После «Принимаю» повторно не показывается."""

        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: email={user['email']}")

        with allure.step("2. Логин, анкета «данные о себе», тур онбординга"):
            LoginPage(page).login(user["email"], user["password"], handle_onboarding=False)
            sidebar = UserSidebarPage(page)
            sidebar.dismiss_anketa()
            sidebar.pass_onboarding()  # dismiss_popups() здесь не годится: он сам жмёт «Принимаю»
            page.screenshot(path="allure-results/cookie_banner_01_after_login.png")
            allure.attach.file("allure-results/cookie_banner_01_after_login.png", "После входа",
                               allure.attachment_type.PNG)

        with allure.step("3. Cookie-баннер виден"):
            banner = page.locator("div:has-text('Мы используем файлы cookie')").last
            expect(banner).to_be_visible(timeout=15000)
            logger.info("Cookie-баннер найден")

        with allure.step("4. Ссылка «Политикой…» открывается в новой вкладке"):
            policy_link = page.locator("a:has-text('Политикой')").first
            expect(policy_link).to_be_visible(timeout=5000)
            with page.context.expect_page() as new_page_info:
                policy_link.click()
            policy_page = new_page_info.value
            # Внешний сайт ranepa.ru со своими счётчиками — ждём только DOM, не тишину сети.
            policy_page.wait_for_load_state("domcontentloaded")
            policy_page.screenshot(path="allure-results/cookie_banner_02_policy.png")
            allure.attach.file("allure-results/cookie_banner_02_policy.png", "Страница политики",
                               allure.attachment_type.PNG)
            policy_page.close()

        with allure.step("5. Нажать «Принимаю» — баннер скрывается"):
            page.locator("button:has-text('Принимаю')").first.click()
            expect(banner).to_be_hidden(timeout=5000)

        with allure.step("6. После перезагрузки страницы баннер не показывается повторно"):
            page.reload()
            sidebar.wait_loaded()
            sidebar.pass_onboarding()
            page.screenshot(path="allure-results/cookie_banner_03_after_reload.png")
            allure.attach.file("allure-results/cookie_banner_03_after_reload.png", "После перезагрузки",
                               allure.attachment_type.PNG)
            expect(page.locator("div:has-text('Мы используем файлы cookie')").last).to_be_hidden(timeout=5000)
            logger.info("После принятия баннер не повторяется")
