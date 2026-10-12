import allure
from playwright.sync_api import expect
import pytest
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from ui.pages.region_page import RegionPage
from utils.logger import logger
from api.helpers.expectations import expect_status


@allure.feature("UI Tests")
@allure.story("CAS Flow")
class TestCasFlow:

    @allure.title("Пользователь CAS: логин → регион → онбординг → ЛК")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.smoke
    def test_cas_login_and_redirect(self, page, env, api_client, omt_cas_endpoint, external_cas_endpoint):
        from api.helpers.data_generator import generate_cas_payload, generate_external_cas_user_payload

        # ========== API ==========
        with allure.step("1. Создать связь CAS"):
            cas_payload = generate_cas_payload()
            cas_data = omt_cas_endpoint.create_tenant_org_location(cas_payload)
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
            # api_client — уже авторизованная фикстура вместо отдельного
            # ApiClient(cookie=settings.DEVELOP_COOKIE)/сырых requests с ручной кукой:
            # settings.DEVELOP_COOKIE всегда указывает на develop независимо от --env
            # и раньше давал 401 при попытке использовать его напрямую.
            get_resp = api_client.get(f"/users/{user_id}")
            expect_status(get_resp, 200)
            user_attrs = get_resp.json()["data"]["attributes"]
            user_attrs["tags"] = []
            user_attrs["password"] = "SecurePass123"
            user_attrs["system_password"] = "SecurePass123"
            resp = api_client.put(f"/users/{user_id}", json={"data": {"attributes": user_attrs}})
            expect_status(resp, 200)
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
            region_page.select_municipality("Центральный округ")
            region_page.accept_agreement()
            region_page.click_continue()
            page.screenshot(path="allure-results/cas_02_region.png")
            allure.attach.file("allure-results/cas_02_region.png", "Регион выбран", allure.attachment_type.PNG)

        with allure.step("5. Онбординг"):
            # Новые модалки после анкеты региона: уведомление «Вы отказались от рассылки» («Понятно»),
            # затем вводное окно тура «Интерактивное руководство» → шаги → «Завершить». Всё закрывает общий помощник.
            notice_ok = page.locator("button:has-text('Понятно')").first
            if notice_ok.is_visible(timeout=5000):
                notice_ok.click()
                expect(notice_ok).to_be_hidden(timeout=5000)
            UserSidebarPage(page).dismiss_popups()
            page.screenshot(path="allure-results/cas_03_onboarding.png")
            allure.attach.file("allure-results/cas_03_onboarding.png", "Онбординг", allure.attachment_type.PNG)

        with allure.step("6. Перейти в ЛК"):
            # cookie-баннер появляется после тура и перекрывает низ страницы — принять до работы с меню
            accept_cookie = page.locator("button:has-text('Принимаю')").first
            if accept_cookie.is_visible(timeout=3000):
                accept_cookie.click()
                expect(accept_cookie).to_be_hidden(timeout=5000)
            page.locator("[data-onboarding-step='user-menu']").first.click()
            lk_item = page.locator("div.v-list-item-title:has-text('Личный кабинет обучающегося')").first
            expect(lk_item).to_be_visible(timeout=10000)
            page.screenshot(path="allure-results/cas_03b_menu.png")
            allure.attach.file("allure-results/cas_03b_menu.png", "Меню пользователя", allure.attachment_type.PNG)

            # Кликаем ЛК — открывается новая вкладка
            with page.context.expect_page() as new_page_info:
                lk_item.click()
            lk_page = new_page_info.value
            lk_page.wait_for_load_state("domcontentloaded")
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
            # login() сам открывает /auth/main и ждёт готовности SPA после входа.
            login_page.login(user_email, "SecurePass123")
            page.locator("[data-onboarding-step='user-menu']").first.click(force=True)
            page.screenshot(path="allure-results/cas_05_no_lk.png")
            allure.attach.file("allure-results/cas_05_no_lk.png", "ЛК отсутствует", allure.attachment_type.PNG)
            assert not page.locator("div.v-list-item-title:has-text('Личный кабинет обучающегося')").is_visible(timeout=3000)
            logger.info("ЛК не отображается")

        with allure.step("9. Очистка"):
            from api.endpoints.users import UsersEndpoint
            UsersEndpoint(api_client).delete(user_id)
            logger.info(f"Пользователь удалён: user_id={user_id}")
            omt_cas_endpoint.delete_tenant_org_location(cas_id)
            logger.info(f"Связь CAS удалена: ID={cas_id}")

        logger.info("CAS Flow завершён!")