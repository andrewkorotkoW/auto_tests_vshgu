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
            assert "/consent" in buk_tab.url, "ожидали страницу согласия БУК"
            buk_tab.screenshot(path=f"allure-results/buk_consent_{user['id']}.png")
            allure.attach.file(f"allure-results/buk_consent_{user['id']}.png", "БУК: согласие с правилами",
                               allure.attachment_type.PNG)

            buk_tab.close()

    @allure.title("Согласие с правилами в БУК → вход в кабинет БУК (сквозной SSO)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.xfail(
        strict=True,
        reason="Стенд БУК (21.09.2026): форма согласия шлёт POST на http://test-dp.ranepa.ru (mixed content, "
               "в Chrome — предупреждение «данные передаются небезопасно»), в ответ отдаёт сырой JSON "
               "{redirect_url}, а сам redirect_url (/asuo/auth?asuo=…) отвечает «Не удалось авторизовать "
               "пользователя». Когда починят — тест станет XPASS и упадёт как strict: снять xfail.",
    )
    def test_buk_consent_leads_into_buk(self, page, env, buk_synced_user):
        import json
        user, payload = buk_synced_user
        sidebar = _login(page, env, user)
        sidebar.open_user_menu()
        with page.expect_popup(timeout=15000) as popup_info:
            sidebar.buk_menu_item().click()
        buk_tab = popup_info.value
        buk_tab.wait_for_load_state("domcontentloaded", timeout=20000)

        with allure.step("1. Страница согласия БУК"):
            assert "/consent" in buk_tab.url, buk_tab.url
            assert buk_tab.locator("text=Согласие с правилами").first.is_visible(timeout=10000)
            form_action = buk_tab.locator("form").first.get_attribute("action") or ""
            allure.attach(form_action, "action формы согласия", allure.attachment_type.TEXT)
            assert form_action.startswith("https://"), f"форма согласия отправляется по незащищённому адресу: {form_action}"

        with allure.step("2. Галка «Даю согласие» → «Подтвердить»"):
            buk_tab.locator("input[type=checkbox]").first.check(force=True)
            buk_tab.locator("button:has-text('Подтвердить'), input[type=submit], a:has-text('Подтвердить')").first.click()
            try:
                buk_tab.wait_for_load_state("networkidle", timeout=30000)
            except Exception:  # noqa: BLE001
                pass
            buk_tab.wait_for_timeout(1000)
            logger.info(f"После подтверждения: {buk_tab.url}")
            allure.attach(buk_tab.url, "URL после подтверждения", allure.attachment_type.TEXT)
            assert not buk_tab.url.startswith("chrome-error://"), "браузер показал страницу ошибки после отправки согласия"
            body = buk_tab.inner_text("body").strip()
            if body.startswith("{"):  # бэкенд вернул JSON вместо редиректа — идём по redirect_url сами
                data = json.loads(body)
                allure.attach(body, "Ответ на согласие (JSON)", allure.attachment_type.JSON)
                assert "redirect_url" in data, data
                buk_tab.goto(data["redirect_url"], wait_until="networkidle")
                buk_tab.wait_for_timeout(1500)

        with allure.step("3. Мы внутри БУК, без ошибки авторизации"):
            buk_tab.screenshot(path=f"allure-results/buk_inside_{user['id']}.png", full_page=True)
            allure.attach.file(f"allure-results/buk_inside_{user['id']}.png", "БУК после согласия", allure.attachment_type.PNG)
            text = buk_tab.inner_text("body")
            assert "test-buk.ranepa.ru" in buk_tab.url and "/consent" not in buk_tab.url, buk_tab.url
            assert "Не удалось авторизовать" not in text and '"error"' not in text, text[:300]
            assert user["surname"] in text or "Выйти" in text or "Личный кабинет" in text, text[:300]
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
