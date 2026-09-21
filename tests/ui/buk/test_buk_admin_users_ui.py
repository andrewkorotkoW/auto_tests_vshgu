import allure
import pytest

from api.helpers.data_generator import generate_buk_user_payload
from config.environments import get_credentials
from ui.pages.login_page import LoginPage
from ui.pages.admin_users_page import AdminUsersPage, BUK_SYNCED_TOOLTIP
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

GREEN = "rgb(126, 211, 33)"


def _shot(page, name, title):
    page.screenshot(path=f"allure-results/{name}.png")
    allure.attach.file(f"allure-results/{name}.png", title, allure.attachment_type.PNG)


@pytest.fixture
def admin_users(page, env):
    """Вход администратором через форму (<ENV>_ADMIN_LOGIN, иначе <ENV>_LOGIN — admin3) → База пользователей."""
    login, password = get_credentials(env.name, role="admin")
    if not login or not password:
        pytest.skip(f"Нет учётки администратора для {env.name} в .env")
    LoginPage(page).login(login, password, base_url=env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()
    admin = AdminUsersPage(page)
    admin.open(env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()
    return admin


@pytest.fixture
def buk_synced_user(created_user, external_buk_endpoint):
    user = created_user()
    payload = generate_buk_user_payload(from_user=user)
    external_buk_endpoint.post_user(payload)
    result = external_buk_endpoint.wait_for_match(payload)
    assert result["user"]["sync_status"] == "synced", result
    return user, payload


@allure.feature("External BUK API")
@allure.story("UI: админка, колонка «Синхронизация»")
class TestBukAdminUsersUI:

    @allure.title("Админ: в базе пользователей у синхронизированного с БУК стоит чип «БУК», подсказка «Синхронизирован»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_sees_buk_chip_with_tooltip(self, page, admin_users, buk_synced_user):
        user, _ = buk_synced_user
        with allure.step("Найти пользователя в базе пользователей"):
            row = admin_users.row_for(user)
            assert str(user["id"]) in row.inner_text(), row.inner_text()
        with allure.step("В колонке «Синхронизация» есть чип «БУК» с зелёной иконкой"):
            chip = admin_users.sync_chip(row, "БУК")
            assert chip.is_visible(timeout=5000), "чип «БУК» не отображается"
            color = admin_users.chip_icon_color(chip)
            allure.attach(color, "Цвет иконки", allure.attachment_type.TEXT)
            assert color == GREEN, f"иконка БУК должна быть зелёной, сейчас {color}"
        with allure.step("Навести курсор на «БУК»: подсказка «Синхронизирован»"):
            tooltip = admin_users.tooltip_of(chip)
            _shot(page, f"admin_buk_tooltip_{user['id']}", "Подсказка БУК")
            assert tooltip == BUK_SYNCED_TOOLTIP, f"подсказка: {tooltip!r}"

    @allure.title("Админ: у пользователя без синхронизации чипа «БУК» нет, «КАС» показывает ожидание")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    def test_admin_no_buk_chip_for_unsynced(self, page, admin_users, created_user):
        user = created_user()
        row = admin_users.row_for(user)
        chips = [c.strip() for c in admin_users.sync_chips(row).all_inner_texts()]
        _shot(page, f"admin_no_buk_{user['id']}", "Колонка Синхронизация без БУК")
        assert "БУК" not in chips, chips
        kas = admin_users.sync_chip(row, "КАС")
        if kas.count():
            tooltip = admin_users.tooltip_of(kas)
            assert tooltip and "ожидании" in tooltip.lower(), tooltip

    @allure.title("Админ: после разрыва связи (DELETE от БУК) чип «БУК» больше не «Синхронизирован»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    def test_admin_buk_chip_after_unsync(self, page, admin_users, buk_synced_user, external_buk_endpoint):
        user, payload = buk_synced_user
        with allure.step("До разрыва: «Синхронизирован»"):
            row = admin_users.row_for(user)
            assert admin_users.tooltip_of(admin_users.sync_chip(row, "БУК")) == BUK_SYNCED_TOOLTIP
        with allure.step("DELETE от БУК"):
            result = external_buk_endpoint.delete_user(payload["buk_user_id"])
            assert result["user"]["sync_status"] == "unsynced", result
        with allure.step("После обновления таблицы чип либо исчез, либо подсказка уже не «Синхронизирован»"):
            page.reload()
            admin_users.wait_loaded()
            UserSidebarPage(page).dismiss_popups()
            row = admin_users.row_for(user)
            chip = admin_users.sync_chip(row, "БУК")
            if chip.count() and chip.is_visible(timeout=2000):
                tooltip = admin_users.tooltip_of(chip)
                allure.attach(str(tooltip), "Подсказка после разрыва", allure.attachment_type.TEXT)
                assert tooltip != BUK_SYNCED_TOOLTIP, tooltip
                logger.info(f"После разрыва чип БУК показывает: {tooltip!r}")
            else:
                logger.info("После разрыва чип БУК не отображается")
            _shot(page, f"admin_buk_after_unsync_{user['id']}", "После разрыва связи")
