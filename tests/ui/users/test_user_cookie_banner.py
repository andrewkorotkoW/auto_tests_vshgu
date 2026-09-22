import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("User Cookie Banner")
class TestUserCookieBanner:

    @allure.title("Пользователь: логин → онбординг → ссылка «Политикой» → закрыть вкладку → «Принимаю»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Дефект стенда develop: cookie-баннер согласия не появляется вовсе даже "
            "после логина свежего пользователя, закрытия анкеты «данные о себе» и "
            "полного прохождения онбординга (проверено ожиданием 10с)."
        ),
    )
    def test_user_cookie_banner(self, page, created_user):
        """API: создать пользователя → UI: логин → онбординг → баннер → политика → принять."""

        # ========== API ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: email={user['email']}, password={user['password']}")

        # ========== UI ==========
        with allure.step("2. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            UserSidebarPage(page).dismiss_anketa()
            page.screenshot(path="allure-results/cookie_banner_01_login.png")
            allure.attach.file("allure-results/cookie_banner_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("3. Онбординг"):
            sidebar = UserSidebarPage(page)
            sidebar.pass_onboarding()
            sidebar.close_tour_dialog()
            page.screenshot(path="allure-results/cookie_banner_02_onboarding.png")
            allure.attach.file("allure-results/cookie_banner_02_onboarding.png", "Онбординг",
                               allure.attachment_type.PNG)

        with allure.step("4. Найти cookie-баннер"):
            banner = page.locator("div:has-text('Мы используем файлы cookie')").first
            if banner.count() == 0:
                banner = page.locator("[data-qa='cookie-banner'], .cookie-banner, #cookie-banner").first
            assert banner.is_visible(timeout=10000), "Cookie-баннер не отображается"
            logger.info("Cookie-баннер найден")
            page.screenshot(path="allure-results/cookie_banner_03_banner.png")
            allure.attach.file("allure-results/cookie_banner_03_banner.png", "Cookie-баннер",
                               allure.attachment_type.PNG)

        with allure.step("5. Кликнуть ссылку «Политикой…» и закрыть вкладку"):
            policy_link = banner.locator("a:has-text('Политикой')")
            if policy_link.count() == 0:
                policy_link = page.locator("a:has-text('Политикой в отношении использования файлов Cookie')").first
            assert policy_link.is_visible(timeout=5000), "Ссылка на политику cookie не найдена"

            with page.context.expect_page() as new_page_info:
                policy_link.click(force=True)
            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            new_page.screenshot(path="allure-results/cookie_banner_04_policy.png")
            allure.attach.file("allure-results/cookie_banner_04_policy.png", "Страница политики",
                               allure.attachment_type.PNG)
            logger.info("Ссылка на политику открыта")
            new_page.close()
            logger.info("Вкладка с политикой закрыта")

        with allure.step("6. Нажать кнопку «Принимаю»"):
            accept_btn = page.locator(
                "button:has-text('Принимаю'), button:has-text('Принять'), button:has-text('Согласен')").first
            if accept_btn.count() == 0:
                accept_btn = page.locator("span:has-text('Принимаю'), span:has-text('Принять')").first
            assert accept_btn.is_visible(timeout=5000), "Кнопка 'Принимаю' не найдена"
            accept_btn.click(force=True)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/cookie_banner_05_accepted.png")
            allure.attach.file("allure-results/cookie_banner_05_accepted.png", "Cookie приняты",
                               allure.attachment_type.PNG)
            logger.info("Cookie приняты")

        with allure.step("7. Убедиться, что баннер исчез"):
            assert not banner.is_visible(timeout=5000), "Баннер не исчез после принятия"
            logger.info("Баннер исчез")

        logger.info("Тест cookie-баннера завершён!")