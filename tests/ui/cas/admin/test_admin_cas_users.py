import allure
import pytest
from playwright.sync_api import expect
from ui.pages.admin_users_page import AdminUsersPage, BUK_SYNCED_TOOLTIP
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

GREEN = "rgb(126, 211, 33)"


@allure.feature("UI Tests")
@allure.story("Admin CAS Users")
class TestAdminCasUsers:

    @allure.title("Админ: проверка CAS-пользователя в Базе Пользователей")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_cas_user(self, admin_page, env, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_user_payload
        from api.endpoints.users import UsersEndpoint

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать CAS-пользователя"):
            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")
            logger.info(f"CAS пользователь: ID={user_id}, ФИО={user_payload['surname']} {user_payload['name']}")

        # ========== UI ==========
        # Интерфейс обновился (15.10.2026): статус синхронизации теперь — чип с иконкой
        # прямо в колонке «Синхронизация» списка «База Пользователей» (как у БУК, см.
        # tests/ui/buk/test_buk_admin_users_ui.py), а не текст внутри карточки пользователя —
        # заходить в карточку больше не нужно. admin_page — уже авторизованная под
        # администратором страница (storage_state).
        admin_users = AdminUsersPage(admin_page)
        with allure.step("3. Открыть «Базу Пользователей» и найти CAS-пользователя"):
            shell = UserSidebarPage(admin_page)
            shell.dismiss_popups()
            admin_page.goto(f"{env.ui_base_url}/admin/users")
            # /admin/users держит фоновый поллинг — networkidle здесь ждал 21-22с
            # (разведка 12.10.2026); нужна только готовность таблицы.
            shell.wait_loaded()
            row = admin_users.row_for(user_payload)
            admin_page.screenshot(path="allure-results/cas_admin_user.png")
            allure.attach.file("allure-results/cas_admin_user.png", "Пользователь КАС", allure.attachment_type.PNG)

        with allure.step("4. В колонке «Синхронизация» есть чип «КАС» с зелёной иконкой"):
            chip = admin_users.sync_chip(row, "КАС")
            assert chip.is_visible(timeout=5000), "чип «КАС» не отображается"
            color = admin_users.chip_icon_color(chip)
            allure.attach(color, "Цвет иконки", allure.attachment_type.TEXT)
            assert color == GREEN, f"иконка КАС должна быть зелёной, сейчас {color}"

        with allure.step("5. Навести курсор на «КАС»: подсказка «Синхронизирован»"):
            tooltip = admin_users.tooltip_of(chip)
            admin_page.screenshot(path="allure-results/cas_admin_user_synced.png")
            allure.attach.file("allure-results/cas_admin_user_synced.png", "Синхронизация КАС",
                               allure.attachment_type.PNG)
            assert tooltip == BUK_SYNCED_TOOLTIP, f"подсказка: {tooltip!r}"

        with allure.step("5.1. Снять синхронизацию (API)"):
            external_cas_endpoint.delete_user(user_id)
            logger.info("Синхронизация снята")

        with allure.step("5.2. Обновить страницу и проверить, что подсказка больше не «Синхронизирован»"):
            # Даже с поллингом стенд develop иногда не успевает отразить снятую
            # синхронизацию сразу — тот же приём, что был в прежней версии теста.
            admin_page.reload()
            shell.wait_loaded()
            row = admin_users.row_for(user_payload)
            chip = admin_users.sync_chip(row, "КАС")
            if chip.count() and chip.is_visible(timeout=10000):
                tooltip = admin_users.tooltip_of(chip)
                allure.attach(str(tooltip), "Подсказка после разрыва", allure.attachment_type.TEXT)
                assert tooltip != BUK_SYNCED_TOOLTIP, tooltip
                logger.info(f"После разрыва чип КАС показывает: {tooltip!r}")
            else:
                logger.info("После разрыва чип КАС не отображается")
            admin_page.screenshot(path="allure-results/cas_admin_user_unsynced.png")
            allure.attach.file("allure-results/cas_admin_user_unsynced.png", "Синхронизация снята",
                               allure.attachment_type.PNG)

        # ========== CLEANUP ==========
        with allure.step("6. Очистка"):
            # Снять синхронизацию (если ещё не снята)
            external_cas_endpoint.delete_user(user_id)
            # Удалить обычного пользователя через уже авторизованную фикстуру api_client
            # (не отдельный ApiClient(cookie=settings.DEVELOP_COOKIE) — эта кука в .env
            # не проходит логин и раньше давала 401 при попытке использовать её напрямую).
            UsersEndpoint(api_client).delete(user_id)
            logger.info(f"Пользователь удалён: ID={user_id}")
            # Удалить связь CAS
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info("Очистка завершена")
