import allure
import pytest

from api.helpers.data_generator import generate_buk_user_payload
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage, BUK_MENU_LABEL, BUK_LINK_PART
from utils.logger import logger


def _shot(page, name, title):
    page.screenshot(path=f"allure-results/{name}.png")
    allure.attach.file(f"allure-results/{name}.png", title, allure.attachment_type.PNG)


@pytest.fixture
def buk_synced_user(created_user, external_buk_endpoint):
    """API: пользователь АСУО + приём в БУК → дождаться sync_status=synced."""
    user = created_user()
    payload = generate_buk_user_payload(from_user=user)
    external_buk_endpoint.post_user(payload)
    result = external_buk_endpoint.wait_for_match(payload)
    assert result["user"]["sync_status"] == "synced", result
    logger.info(f"Пользователь {user['id']} синхронизирован с БУК как {payload['buk_user_id']}")
    return user, payload


def _login(page, env, user) -> UserSidebarPage:
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    sidebar = UserSidebarPage(page)
    sidebar.dismiss_popups()
    return sidebar


@allure.feature("External BUK API")
@allure.story("UI: кнопка АИС «БУК «Перспектива»» в меню пользователя")
class TestBukUserMenuUI:

    @allure.title("Синхронизированный с БУК пользователь: вход → в меню профиля есть «АИС «БУК «Перспектива»»» → переход")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_buk_button_for_synced_user(self, page, env, buk_synced_user):
        user, payload = buk_synced_user

        with allure.step("1. Войти под пользователем"):
            sidebar = _login(page, env, user)
            assert "/auth" not in page.url, page.url
            assert user["surname"] in sidebar.user_name()

        with allure.step("2. Открыть меню под ФИО: пункт БУК отображается"):
            items = sidebar.user_menu_items()
            _shot(page, f"buk_menu_{user['id']}", "Меню пользователя")
            assert any(BUK_MENU_LABEL in i for i in items), f"Нет пункта БУК в меню: {items}"
            item = sidebar.buk_menu_item()
            assert item.is_visible(timeout=3000)
            href = item.get_attribute("href") or ""
            assert BUK_LINK_PART in href and href.startswith("https://"), href
            assert item.get_attribute("target") == "_blank", "ссылка БУК должна открываться в новой вкладке"
            logger.info(f"Пункт БУК: {href}")

        with allure.step("3. Переход по кнопке: открывается новая вкладка с переходом в БУК"):
            with page.expect_popup(timeout=15000) as popup_info:
                item.click()
            buk_tab = popup_info.value
            try:
                buk_tab.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception as exc:  # noqa: BLE001 — внешний стенд может быть недоступен из сети прогона
                logger.warning(f"Внешняя вкладка БУК не догрузилась: {exc}")
            logger.info(f"Новая вкладка: {buk_tab.url}")
            allure.attach(buk_tab.url, "URL новой вкладки", allure.attachment_type.TEXT)
            assert buk_tab.url.startswith("https://"), buk_tab.url
            buk_tab.close()

    @allure.title("Пользователь без синхронизации с БУК: пункта БУК в меню нет")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    def test_no_buk_button_for_unsynced_user(self, page, env, created_user, external_buk_endpoint):
        user = created_user()
        sidebar = _login(page, env, user)
        items = sidebar.user_menu_items()
        _shot(page, f"buk_menu_absent_{user['id']}", "Меню пользователя без БУК")
        assert "Мой профиль" in " ".join(items), items
        assert not any("БУК" in i for i in items), f"Пункт БУК не должен показываться: {items}"

    @allure.title("После разрыва связи (DELETE от БУК) пункт БУК исчезает из меню")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    def test_buk_button_disappears_after_unsync(self, page, env, buk_synced_user, external_buk_endpoint):
        user, payload = buk_synced_user
        sidebar = _login(page, env, user)
        with allure.step("До разрыва пункт есть"):
            assert any(BUK_MENU_LABEL in i for i in sidebar.user_menu_items())
            sidebar.close_menu()
        with allure.step("DELETE от БУК → unsynced"):
            result = external_buk_endpoint.delete_user(payload["buk_user_id"])
            assert result["user"]["sync_status"] == "unsynced", result
        with allure.step("После перезагрузки страницы пункта нет"):
            page.reload()
            sidebar.wait_loaded()
            sidebar.dismiss_popups()
            items = sidebar.user_menu_items()
            _shot(page, f"buk_menu_after_unsync_{user['id']}", "Меню после разрыва связи")
            assert not any("БУК" in i for i in items), items
