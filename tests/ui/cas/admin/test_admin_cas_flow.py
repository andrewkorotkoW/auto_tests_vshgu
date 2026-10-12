import allure
import pytest
from playwright.sync_api import expect
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Admin CAS Flow")
class TestAdminCasFlow:

    @allure.title("Админ: проверка синхронизации программы и потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_cas_program(self, admin_page, env, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_program_payload, generate_external_cas_stream_payload

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу"):
            program_payload = generate_external_cas_program_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            data = external_cas_endpoint.create_program(program_payload)
            program_id = data.get("program_id")

        with allure.step("3. Создать поток"):
            stream_payload = generate_external_cas_stream_payload()
            stream_data = external_cas_endpoint.create_stream(program_id, stream_payload)
            stream_id = stream_data.get("stream_id")

        # ========== UI ==========
        # admin_page — уже авторизованная под администратором страница (storage_state),
        # логин через форму под settings.TEST_USER_EMAIL и клик по «Админка» в меню
        # пользователя (ui/pages/admin_page.py.go_to_admin) не нужны. Вкладки открываем
        # прямыми URL с ?i=<index> (0=Потоки, 1=Описание у программы) вместо клика по
        # span-кнопке вкладки — на develop такой клик не переключает SPA-контент.
        program_url = f"{env.ui_base_url}/admin/programs/{program_id}"
        stream_url = f"{env.ui_base_url}/admin/programs/{program_id}/streams/{stream_id}"
        with allure.step("4. Открыть программу → Описание"):
            shell = UserSidebarPage(admin_page)
            shell.dismiss_popups()
            admin_page.goto(f"{program_url}?i=1")
            shell.wait_loaded()
            admin_page.screenshot(path="allure-results/cas_admin_program.png")

        with allure.step("5. Проверить синхронизацию (зелёная круглая кнопка)"):
            # expect() поллит, а не проверяет один раз сразу после networkidle: контент
            # вкладки «Описание» дорисовывается асинхронно уже после networkidle (SPA).
            expect(admin_page.locator("button.v-btn--round[style*='213, 239, 209']").first).to_be_visible(timeout=10000)
            logger.info("Программа синхронизирована")
            admin_page.screenshot(path="allure-results/cas_admin_program_synced.png")
            allure.attach.file("allure-results/cas_admin_program_synced.png", "Программа синхронизирована",
                               allure.attachment_type.PNG)

        with allure.step("6. Открыть поток"):
            admin_page.goto(stream_url)

        with allure.step("7. Проверить синхронизацию потока"):
            expect(admin_page.locator("button.v-btn--round[style*='213, 239, 209']").first).to_be_visible(timeout=10000)
            logger.info("Поток синхронизирован")
            admin_page.screenshot(path="allure-results/cas_admin_stream_synced.png")
            allure.attach.file("allure-results/cas_admin_stream_synced.png", "Поток синхронизирован",
                               allure.attachment_type.PNG)

        with allure.step("8. Снять синхронизацию программы (API)"):
            external_cas_endpoint.delete_program(program_id)
            logger.info("Синхронизация программы снята")

        with allure.step("9. Обновить страницу программы и проверить отсутствие синхронизации"):
            admin_page.goto(f"{program_url}?i=1")
            # Негативная проверка (count 0) прошла бы и на ещё не отрисованной странице —
            # ждём, пока уйдут индикаторы загрузки.
            shell.wait_loaded()
            expect(admin_page.locator("button.v-btn--round[style*='213, 239, 209']")).to_have_count(0, timeout=10000)
            logger.info("Синхронизация снята — зелёная кнопка отсутствует")
            admin_page.screenshot(path="allure-results/cas_admin_unsynced.png")
            allure.attach.file("allure-results/cas_admin_unsynced.png", "Синхронизация снята",
                               allure.attachment_type.PNG)

        with allure.step("10. Проверить отсутствие синхронизации потока"):
            admin_page.goto(stream_url)
            shell.wait_loaded()
            expect(admin_page.locator("button.v-btn--round[style*='213, 239, 209']")).to_have_count(0, timeout=10000)
            admin_page.screenshot(path="allure-results/cas_admin_stream_unsynced.png")
            allure.attach.file("allure-results/cas_admin_stream_unsynced.png", "Поток не синхронизирован",
                               allure.attachment_type.PNG)

        # ========== CLEANUP ==========
        with allure.step("11. Очистка"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            from api.endpoints.programs import ProgramsEndpoint
            ProgramsEndpoint(api_client).mass_delete([program_id])
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info("Очистка завершена")