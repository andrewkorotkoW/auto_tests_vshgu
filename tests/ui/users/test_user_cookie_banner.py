import allure
import pytest
from playwright.sync_api import expect

from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Cookie Banner")
class TestUserCookieBanner:

    @allure.title("Cookie-баннер на странице входа: ссылка «Политикой», «Принимаю», после входа не повторяется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Баг develop (подтверждён 23.09.2026): cookie-баннер не показывается на странице входа "
            "/auth/main, а появляется уже внутри системы после прохождения онбординга и пропадает при "
            "переходе на другую страницу. Разбор: qa_analysis/cases/DEVELOP_cookie_banner_2026-09-23. "
            "Когда починят, тест пройдёт — снять маркер."
        ),
    )
    def test_user_cookie_banner(self, page, env, created_user):
        """Баннер ожидается до авторизации. После «Принимаю» и входа он не должен показываться снова."""

        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: email={user['email']}")

        with allure.step("2. Открыть страницу входа без авторизации — баннер cookie виден"):
            page.goto(f"{env.ui_base_url}/auth/main")
            page.wait_for_load_state("networkidle")
            banner = page.locator("div:has-text('Мы используем файлы cookie')").last
            page.screenshot(path="allure-results/cookie_banner_01_login_page.png")
            allure.attach.file("allure-results/cookie_banner_01_login_page.png", "Страница входа",
                               allure.attachment_type.PNG)
            expect(banner).to_be_visible(timeout=10000)
            logger.info("Cookie-баннер найден на странице входа")

        with allure.step("3. Ссылка «Политикой…» открывается в новой вкладке"):
            policy_link = page.locator("a:has-text('Политикой')").first
            expect(policy_link).to_be_visible(timeout=5000)
            with page.context.expect_page() as new_page_info:
                policy_link.click()
            policy_page = new_page_info.value
            policy_page.wait_for_load_state("networkidle")
            policy_page.screenshot(path="allure-results/cookie_banner_02_policy.png")
            allure.attach.file("allure-results/cookie_banner_02_policy.png", "Страница политики",
                               allure.attachment_type.PNG)
            policy_page.close()

        with allure.step("4. Нажать «Принимаю» — баннер скрывается"):
            page.locator("button:has-text('Принимаю')").first.click()
            expect(banner).to_be_hidden(timeout=5000)

        with allure.step("5. Войти, пройти анкету и онбординг — баннер не показывается повторно"):
            LoginPage(page).login(user["email"], user["password"], handle_onboarding=False)
            sidebar = UserSidebarPage(page)
            sidebar.dismiss_anketa()
            sidebar.pass_onboarding()
            page.screenshot(path="allure-results/cookie_banner_03_after_login.png")
            allure.attach.file("allure-results/cookie_banner_03_after_login.png", "После входа",
                               allure.attachment_type.PNG)
            expect(page.locator("div:has-text('Мы используем файлы cookie')").last).to_be_hidden(timeout=3000)
            logger.info("После принятия баннер не повторяется")
