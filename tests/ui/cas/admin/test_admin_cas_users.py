import allure
import pytest
from playwright.sync_api import expect
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


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
            user_fio = f"{user_payload['surname']} {user_payload['name']} {user_payload['patronymic']}"
            logger.info(f"CAS пользователь: ID={user_id}, ФИО={user_fio}")

        # ========== UI ==========
        # admin_page — уже авторизованная под администратором страница (storage_state),
        # логин через форму под settings.TEST_USER_EMAIL и клик по «Админка» в меню
        # пользователя (ui/pages/admin_page.py.go_to_admin) не нужны.
        with allure.step("3. Открыть «Базу Пользователей»"):
            shell = UserSidebarPage(admin_page)
            shell.dismiss_popups()
            admin_page.goto(f"{env.ui_base_url}/admin/users")
            # /admin/users держит фоновый поллинг — networkidle здесь ждал 21–22 с
            # (разведка 12.10.2026); нужна только готовность таблицы.
            shell.wait_loaded()

        with allure.step("4. Найти пользователя по ФИО"):
            admin_page.locator('[data-qa="km-search"]').fill(user_fio)
            admin_page.locator(f"text={user_fio}").first.click(force=True)
            shell.wait_loaded()
            admin_page.screenshot(path="allure-results/cas_admin_user.png")
            allure.attach.file("allure-results/cas_admin_user.png", "Пользователь КАС", allure.attachment_type.PNG)

        with allure.step("5. Проверить тип регистрации — КАС"):
            assert admin_page.locator("text=КАС").first.is_visible(timeout=5000), "Тип регистрации не КАС!"
            logger.info("Тип регистрации: КАС подтверждён")

        with allure.step("6. Проверить статус синхронизации"):
            synced_chip = admin_page.locator("span.v-chip__content:has-text('Синхронизирован')")
            assert synced_chip.first.is_visible(timeout=5000), "Статус 'Синхронизирован' не отображается!"

            assert admin_page.locator("text=Синхронизация с КАС").first.is_visible(timeout=3000), "Заголовок не отображается!"

            logger.info("Синхронизация с КАС подтверждена")
            admin_page.screenshot(path="allure-results/cas_admin_user_synced.png")
            allure.attach.file("allure-results/cas_admin_user_synced.png", "Синхронизация КАС",
                               allure.attachment_type.PNG)

        with allure.step("6.1. Снять синхронизацию (API)"):
            external_cas_endpoint.delete_user(user_id)
            logger.info("Синхронизация снята")

        with allure.step("6.2. Обновить страницу и проверить отсутствие синхронизации"):
            admin_page.reload()
            shell.wait_loaded()
            # Повторный поиск
            admin_page.locator('[data-qa="km-search"]').fill(user_fio)
            admin_page.locator(f"text={user_fio}").first.click(force=True)
            shell.wait_loaded()

            # is_visible() не ждёт — однократная проверка DOM, без поллинга; заменено на
            # expect(...).to_be_hidden() — тот же приём, что в соседних CAS/UI тестах (см.
            # test_cas_flow.py, test_user_cookie_banner.py). Даже с 10с поллинга стенд develop
            # иногда не успевает отразить снятую синхронизацию в карточке — см. xfail на тесте.
            expect(admin_page.locator("span.v-chip__content:has-text('Синхронизирован')").first).to_be_hidden(
                timeout=10000)
            admin_page.screenshot(path="allure-results/cas_admin_user_unsynced.png")
            allure.attach.file("allure-results/cas_admin_user_unsynced.png", "Синхронизация снята",
                               allure.attachment_type.PNG)
            logger.info("Синхронизация снята — статус исчез")

        # ========== CLEANUP ==========
        with allure.step("7. Очистка"):
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
