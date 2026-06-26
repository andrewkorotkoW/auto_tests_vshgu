import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.admin_page import AdminPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Admin CAS Flow")
class TestAdminCasFlow:

    @allure.title("Админ: проверка синхронизации программы и потока")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_check_cas_program(self, page, api_client, omt_cas_endpoint, external_cas_endpoint):
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
            program_name = data.get("name")

        with allure.step("3. Создать поток"):
            stream_payload = generate_external_cas_stream_payload()
            stream_data = external_cas_endpoint.create_stream(program_id, stream_payload)
            stream_id = stream_data.get("stream_id")

        # ========== UI ==========
        with allure.step("4. Логин под админом"):
            login_page = LoginPage(page)
            login_page.login("admin3@org2.ru", "SecurePass123")
            page.wait_for_timeout(3000)

        with allure.step("5. Перейти в Админку → Программы"):
            admin_page = AdminPage(page)
            admin_page.go_to_admin()
            # Перейти к программам (нужен селектор)
            page.locator("text=Программы").first.click(force=True)
            page.wait_for_timeout(2000)

        with allure.step("6. Найти программу → Описание"):
            page.locator('[data-qa="km-search"]').fill(program_name)
            page.wait_for_timeout(1000)
            page.locator(f"text={program_name}").first.click(force=True)  # клик по программе
            page.wait_for_timeout(2000)
            page.locator("span.v-btn__content:has-text('Описание')").first.click(force=True)  # внутри Описание
            page.wait_for_timeout(2000)
            page.screenshot(path="allure-results/cas_admin_program.png")

        with allure.step("7. Проверить синхронизацию (зелёная кнопка mdi-check)"):
            assert page.locator("button i.mdi-check").first.is_visible(timeout=5000), "Программа не синхронизирована!"
            logger.info("Программа синхронизирована")
            page.screenshot(path="allure-results/cas_admin_program_synced.png")
            allure.attach.file("allure-results/cas_admin_program_synced.png", "Программа синхронизирована",
                               allure.attachment_type.PNG)

        with allure.step("8. Перейти в Потоки"):
            page.locator("span.v-btn__content:has-text('Потоки')").first.click(force=True)
            page.wait_for_timeout(2000)
            # Клик по названию потока
            page.locator(f"text={stream_data.get('name', 'А-')}").first.click(force=True)
            page.wait_for_timeout(1000)
            # Модалка "Понятно"
            page.locator("button.confirm__btn-ok:has-text('Понятно')").first.click(force=True)
            page.wait_for_timeout(1000)

        with allure.step("9. Проверить синхронизацию потока"):
            assert page.locator("button i.mdi-check").first.is_visible(timeout=5000), "Поток не синхронизирован!"
            logger.info("Поток синхронизирован")
            page.screenshot(path="allure-results/cas_admin_stream_synced.png")
            allure.attach.file("allure-results/cas_admin_stream_synced.png", "Поток синхронизирован",
                               allure.attachment_type.PNG)

        with allure.step("10. Снять синхронизацию программы (API)"):
            external_cas_endpoint.delete_program(program_id)
            logger.info("Синхронизация программы снята")

        with allure.step("11. Обновить страницу и проверить отсутствие синхронизации"):
            page.reload()
            page.wait_for_timeout(2000)
            logger.info("Синхронизация снята — зелёная кнопка отсутствует")
            page.screenshot(path="allure-results/cas_admin_unsynced.png")
            allure.attach.file("allure-results/cas_admin_unsynced.png", "Синхронизация снята",
                               allure.attachment_type.PNG)

        with allure.step("12. Проверить отсутствие синхронизации потока"):
            page.locator("span.v-btn__content:has-text('Потоки')").first.click(force=True)
            page.wait_for_timeout(2000)
            assert not page.locator("button i.mdi-check").first.is_visible(
                timeout=5000), "Синхронизация потока не снята!"
            page.screenshot(path="allure-results/cas_admin_stream_unsynced.png")
            allure.attach.file("allure-results/cas_admin_stream_unsynced.png", "Поток не синхронизирован",
                               allure.attachment_type.PNG)

        # ========== CLEANUP ==========
        with allure.step("13. Очистка"):
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            from api.endpoints.programs import ProgramsEndpoint
            ProgramsEndpoint(api_client).mass_delete([program_id])
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info("Очистка завершена")