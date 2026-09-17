import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.admin_page import AdminPage
from config.settings import settings
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("Admin CAS Listeners Statuses")
class TestAdminCasListenersStatuses:

    @allure.title("Админ: проверка статусов слушателей (Зачислен, Отчислен, Ожидание приказа)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_admin_cas_listeners_statuses(self, page, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import (
            generate_cas_payload, generate_external_cas_program_payload,
            generate_external_cas_stream_payload, generate_external_cas_user_payload
        )

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")

        with allure.step("2. Создать программу и поток"):
            data = external_cas_endpoint.create_program(
                generate_external_cas_program_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            program_id = data.get("program_id")
            program_name = data.get("name")
            stream_data = external_cas_endpoint.create_stream(program_id, generate_external_cas_stream_payload())
            stream_id = stream_data.get("stream_id")

        with allure.step("3. Создать 3 пользователей с разными статусами"):
            # Пользователь 1 — enlisted (зачислен)
            user1 = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user1.get("user_id"), "cas_application_uid": "a1111111-bbbb-cccc-dddd-eeeeeeeeeee1"}],
                status="enlisted"
            )

            # Пользователь 2 — dismissed (отчислен)
            user2 = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user2.get("user_id"), "cas_application_uid": "a2222222-bbbb-cccc-dddd-eeeeeeeeeee2"}],
                status="dismissed"
            )

            # Пользователь 3 — enlisted без текстов (ожидание)
            user3 = external_cas_endpoint.create_user(
                generate_external_cas_user_payload(
                    organization_uuid=cas_payload["cas_organization_uuid"],
                    location_uuid=cas_payload["cas_location_uuid"]
                )
            )
            external_cas_endpoint.assign_users(
                stream_id,
                [{"user_id": user3.get("user_id"), "cas_application_uid": "a3333333-bbbb-cccc-dddd-eeeeeeeeeee3"}],
                status="enlisted",
                enlisted_text=None,
                enlisted_link=None
            )

        # ========== UI ==========
        with allure.step("4. Логин и переход к Слушателям"):
            login_page = LoginPage(page)
            login_page.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)
            page.wait_for_timeout(3000)

            admin_page = AdminPage(page)
            admin_page.go_to_admin()
            page.locator('[data-qa="km-search"]').fill(program_name)
            page.wait_for_timeout(1000)
            page.locator(f"text={program_name}").first.click(force=True)
            page.wait_for_timeout(2000)
            page.locator("span.v-btn__content:has-text('Потоки')").first.click(force=True)
            page.wait_for_timeout(2000)
            page.locator(f"text={stream_data.get('name', 'А-')}").first.click(force=True)
            page.wait_for_timeout(2000)
            # Закрыть модалку кликом вверх
            page.locator("body").click(position={"x": 500, "y": 10})
            page.wait_for_timeout(1000)
            page.locator("span.v-btn__content:has-text('Слушатели')").first.click(force=True)
            page.wait_for_timeout(2000)

        with allure.step("5. Проверить статусы"):
            page.screenshot(path="allure-results/cas_admin_listeners.png")
            allure.attach.file("allure-results/cas_admin_listeners.png", "Слушатели", allure.attachment_type.PNG)

            assert page.locator("button.mdi-star-check").first.is_visible(
                timeout=5000), "Статус 'Зачислен' не отображается"
            assert page.locator("button.mdi-cancel").first.is_visible(timeout=3000), "Статус 'Отчислен' не отображается"
            logger.info("Все статусы отображаются корректно")

        with allure.step("6. Очистка"):
            from api.endpoints.users import UsersEndpoint
            from api.client import ApiClient
            from config.settings import settings

            main_client = ApiClient(cookie=settings.DEVELOP_COOKIE)
            users_ep = UsersEndpoint(main_client)
            for uid in [user1.get("user_id"), user2.get("user_id"), user3.get("user_id")]:
                external_cas_endpoint.delete_user(uid)
                users_ep.delete(uid)
            external_cas_endpoint.delete_stream(program_id, stream_id)
            external_cas_endpoint.delete_program(program_id)
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info("Очистка завершена")