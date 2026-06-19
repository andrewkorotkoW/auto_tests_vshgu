import allure
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.region_page import RegionPage
from utils.logger import logger


@allure.feature("UI Tests")
@allure.story("CAS Flow")
class TestCasFlow:

    @allure.title("Пользователь CAS: логин → регион → онбординг → ЛК")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_cas_login_and_redirect(self, page, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_user_payload
        from api.endpoints.omt_cas import OmtCasEndpoint
        from api.client import ApiClient
        from config.settings import settings

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            omt_client = ApiClient(cookie=settings.DEVELOP_COOKIE)
            omt_cas = OmtCasEndpoint(omt_client)
            cas_payload = generate_cas_payload()
            cas_data = omt_cas.create_tenant_org_location(cas_payload)
            cas_id = cas_data.get("id")
            logger.info(f"Связь CAS: ID={cas_id}")

        with allure.step("2. Создать пользователя CAS"):
            user_payload = generate_external_cas_user_payload(
                organization_uuid=cas_payload["cas_organization_uuid"],
                location_uuid=cas_payload["cas_location_uuid"]
            )
            user_data = external_cas_endpoint.create_user(user_payload)
            user_id = user_data.get("user_id")
            user_email = user_payload["email"]
            logger.info(f"Пользователь CAS: user_id={user_id}, email={user_email}")

        with allure.step("2.5. Установить пароль"):
            import requests as req
            get_resp = req.get(
                f"{settings.BASE_URL}/users/{user_id}",
                headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest", "Cookie": f"develop={settings.DEVELOP_COOKIE}"}
            )
            user_attrs = get_resp.json()["data"]["attributes"]
            user_attrs["tags"] = []
            user_attrs["password"] = "SecurePass123"
            user_attrs["system_password"] = "SecurePass123"
            resp = req.put(
                f"{settings.BASE_URL}/users/{user_id}",
                json={"data": {"attributes": user_attrs}},
                headers={"Accept": "application/json", "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "Cookie": f"develop={settings.DEVELOP_COOKIE}"}
            )
            assert resp.status_code == 200, f"Пароль: {resp.status_code} {resp.text}"
            logger.info(f"Пароль установлен для user_id={user_id}")

        # ========== UI ==========
        with allure.step("3. Логин"):
            login_page = LoginPage(page)
            login_page.login(user_email, "SecurePass123")
            page.screenshot(path="allure-results/cas_01_login.png")
            allure.attach.file("allure-results/cas_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("4. Выбрать регион и муниципалитет"):
            region_page = RegionPage(page)
            region_page.select_region("Москва")
            region_page.select_municipality("Южный округ")
            region_page.accept_agreement()
            region_page.click_continue()
            page.screenshot(path="allure-results/cas_02_region.png")
            allure.attach.file("allure-results/cas_02_region.png", "Регион выбран", allure.attachment_type.PNG)

        with allure.step("5. Онбординг"):
            page.wait_for_timeout(2000)
            for btn_text in ["Пройти обучение", "Начать обучение", "Далее", "Продолжить"]:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    page.wait_for_timeout(500)
                    break
            for _ in range(15):
                btn = page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    page.wait_for_timeout(300)
                else:
                    break
            page.screenshot(path="allure-results/cas_03_onboarding.png")
            allure.attach.file("allure-results/cas_03_onboarding.png", "Онбординг", allure.attachment_type.PNG)

        with allure.step("6. Перейти в ЛК"):
            page.locator("[data-onboarding-step='user-menu']").first.click(force=True)
            page.wait_for_timeout(1000)

            # Кликаем ЛК — открывается новая вкладка
            with page.context.expect_page() as new_page_info:
                region_page.go_to_lk()
            lk_page = new_page_info.value
            lk_page.wait_for_load_state("networkidle")
            lk_page.wait_for_timeout(3000)
            lk_page.screenshot(path="allure-results/cas_04_lk.png")
            allure.attach.file("allure-results/cas_04_lk.png", "Личный кабинет", allure.attachment_type.PNG)
            logger.info("Перешли в Личный кабинет")
            lk_page.close()

        with allure.step("7. Снять синхронизацию"):
            success = external_cas_endpoint.delete_user(user_id)
            assert success, f"Не удалось снять синхронизацию {user_id}"
            logger.info(f"Синхронизация CAS снята: user_id={user_id}")

        with allure.step("8. Повторный вход — ЛК не видна"):
            page.context.clear_cookies()
            page.goto(f"{settings.UI_BASE_URL}/auth/main")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            login_page.login(user_email, "SecurePass123")
            page.wait_for_timeout(3000)
            page.locator("[data-onboarding-step='user-menu']").first.click(force=True)
            page.wait_for_timeout(1000)
            page.screenshot(path="allure-results/cas_05_no_lk.png")
            allure.attach.file("allure-results/cas_05_no_lk.png", "ЛК отсутствует", allure.attachment_type.PNG)
            assert not page.locator("div.v-list-item-title:has-text('Личный кабинет обучающегося')").is_visible(timeout=3000)
            logger.info("ЛК не отображается")

        with allure.step("9. Очистка"):
            from api.endpoints.users import UsersEndpoint
            main_client = ApiClient(cookie=settings.DEVELOP_COOKIE)
            UsersEndpoint(main_client).delete(user_id)
            logger.info(f"Пользователь удалён: user_id={user_id}")
            omt_cas.delete_tenant_org_location(cas_id)
            logger.info(f"Связь CAS удалена: ID={cas_id}")

        logger.info("CAS Flow завершён!")