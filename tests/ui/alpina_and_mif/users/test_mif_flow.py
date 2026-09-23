import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("MIF Flow")
class TestMifFlow:

    @allure.title("Проверка доступности MIF после назначения и снятия")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    @pytest.mark.skip(
        reason=(
            "Схема выдачи SSO-токена Альпины/MIF изменилась, сценарий требует "
            "переписывания под новую схему (не дефект стенда)"
        ),
    )
    def test_mif_access(self, page, created_user, mif_endpoint):
        from config.settings import settings

        login_page = LoginPage(page)

        with allure.step("1. Создать пользователя"):
            user = created_user()

        with allure.step("2. Открыть доступ к MIF"):
            mif_endpoint.set_access([user["id"]], True)

        with allure.step("3. Логин и проверка кнопки MIF"):
            login_page.login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

            mif_btn = page.locator("span.nav-item__text:has-text('МИФ')").first
            assert mif_btn.is_visible(timeout=6000), "Кнопка MIF не отображается!"
            page.screenshot(path="allure-results/mif_01_button.png")
            allure.attach.file("allure-results/mif_01_button.png", "Кнопка MIF", allure.attachment_type.PNG)

            # Клик → новая вкладка
            with page.context.expect_page() as new_page_info:
                mif_btn.click(force=True)
            mif_page = new_page_info.value
            mif_page.wait_for_load_state("networkidle")
            # Проверить URL редиректа
            # Примечание: бесшовный OAuth-переход (gosedu → miflib) невозможен в Playwright
            # из-за кросс-доменных ограничений. Тест проверяет, что редирект инициирован.
            try:
                mif_page.wait_for_url(lambda url: "gosedu" in url or "miflib" in url, timeout=settings.UI_TIMEOUT)
            except Exception:
                pass
            assert "gosedu" in mif_page.url or "miflib" in mif_page.url, f"Неверный URL: {mif_page.url}"
            logger.info(f"MIF редирект: {mif_page.url}")
            mif_page.screenshot(path="allure-results/mif_02_page.png")
            mif_page.close()

        with allure.step("4. Закрыть доступ"):
            mif_endpoint.set_access([user["id"]], False)

        with allure.step("5. Повторный вход — кнопки нет"):
            page.context.clear_cookies()
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle")
            login_page.login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

            assert not page.locator("span.nav-item__text:has-text('МИФ')").first.is_visible(timeout=3000), "Кнопка MIF всё ещё видна!"
            page.screenshot(path="allure-results/mif_03_no_access.png")
            allure.attach.file("allure-results/mif_03_no_access.png", "Без MIF", allure.attachment_type.PNG)

        logger.info("MIF Flow завершён!")