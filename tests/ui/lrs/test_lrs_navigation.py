"""UI: навигация между LMS и OpenLRS (`/lrs-admin/*`) и вход — SSO через кнопку «Перейти в
LRS» в «Логах», прямой callback, собственная форма входа OpenLRS, слушатель без прав
админки. Кейсы TC-LRS-001…005, 015 (docs/test_cases/lrs.md), разведка docs/lrs/lrs_recon.md,
page object — ui/pages/lrs_admin_page.py.

SSO (`LrsAdminPage.login_via_sso`, `open_lrs_from_logs`) штатно работает только на k8s —
на develop OAuth-клиент OpenLRS не зарегистрирован в Passport портала (`invalid_client`,
docs/plans/2026-10-14_lrs_mission.md), и кнопки «Перейти в LRS» там нет вовсе. Тесты,
которым нужен реальный вход в OpenLRS (001/002/004/005), помечены `@pytest.mark.env("k8s")`;
003 (чистый контекст без сессии) и 015 (форма входа OpenLRS) не зависят от работоспособности
SSO и не ограничены стендом.

Прогоны — только на k8s после 14:00 14.10.2026 (решение владельца), сейчас только
`pytest --collect-only`."""
import re

import allure
import pytest
from playwright.sync_api import expect

from config.environments import get_credentials
from config.settings import settings
from ui.pages.lrs_admin_page import LrsAdminPage, lrs_base_url, open_lrs_from_logs
from ui.pages.login_page import LoginPage


@allure.feature("LRS")
@allure.story("Навигация и SSO")
class TestLrsNavigation:

    @allure.title("UI: переход из LMS в LRS по кнопке «Перейти в LRS» (SSO)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_admin_opens_lrs_from_logs(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть «Логи» — над таблицей есть кнопка «Перейти в LRS»"):
            LoginPage(page).login(email, password, base_url=env.ui_base_url, handle_onboarding=False)
            page.goto(f"{env.ui_base_url.rstrip('/')}/admin/logs")
            link = page.get_by_role("link", name="Перейти в LRS")
            expect(link).to_be_visible(timeout=settings.UI_TIMEOUT)
            href = link.get_attribute("href") or ""
            assert "/oauth2/auth/callback" in href, f"Неожиданный href кнопки «Перейти в LRS»: {href}"

        with allure.step("2-3. Нажать кнопку — попадаем в OpenLRS под текущим пользователем, без формы входа"):
            open_lrs_from_logs(page)
            expect(page).to_have_title(re.compile(r"Панель управления.*OpenLRS"), timeout=settings.UI_TIMEOUT)
            expect(page.locator('input[name="email"]')).to_have_count(0)

    @allure.title("UI: прямой переход на callback без кнопки логинит авторизованного пользователя")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_callback_logs_in_authorized_user(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть callback LRS, минуя кнопку в «Логах»"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)

        with allure.step("2. Открыть «Хранилища» в той же сессии — повторный вход не требуется"):
            stores = lrs.open_stores()
            expect(page).to_have_url(re.compile(r"/lrs-admin/store$"), timeout=settings.UI_TIMEOUT)
            expect(stores.table).to_be_visible()

    @allure.title("UI: без сессии LMS OpenLRS требует вход")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    def test_lrs_admin_without_session_shows_login(self, page, env):
        with allure.step("1. Открыть /lrs-admin без сессии — редирект на форму входа"):
            page.goto(f"{lrs_base_url(env)}/lrs-admin")
            expect(page).to_have_url(re.compile(r"/lrs-admin/login"), timeout=settings.UI_TIMEOUT)
            expect(page).to_have_title(re.compile(r"Войти.*OpenLRS"), timeout=settings.UI_TIMEOUT)
            expect(page.locator('input[name="email"]')).to_be_visible()
            expect(page.locator('input[name="password"]')).to_be_visible()

        with allure.step("2. Открыть callback без сессии LMS — в LRS не пускает"):
            page.goto(f"{lrs_base_url(env)}/oauth2/auth/callback")
            expect(page).not_to_have_url(re.compile(r"/lrs-admin/store"), timeout=settings.UI_TIMEOUT)

    @allure.title("UI: слушатель без прав админки не видит «Перейти в LRS» и не входит в LRS")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_user_without_admin_rights_cannot_enter_lrs(self, page, env, prepared_user):
        user = prepared_user()

        with allure.step("1. У слушателя в «Логах» нет кнопки «Перейти в LRS»"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            page.goto(f"{env.ui_base_url.rstrip('/')}/admin/logs")
            expect(page.get_by_role("link", name="Перейти в LRS")).to_have_count(0)

        with allure.step("2. OpenLRS не пускает слушателя через callback (иначе — кандидат в дефект)"):
            page.goto(f"{lrs_base_url(env)}/oauth2/auth/callback")
            expect(page).not_to_have_url(re.compile(r"/lrs-admin/store"), timeout=settings.UI_TIMEOUT)

    @allure.title("UI: возврат в LMS по кнопке «Перейти в LMS»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_back_to_lms_button(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Войти в OpenLRS по SSO"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)

        with allure.step("2. «Перейти в LMS» открывает главную LMS без повторного входа"):
            lrs.go_to_lms()
            expect(page).to_have_url(re.compile(r"/admin/programs"), timeout=settings.UI_TIMEOUT)
            expect(page).not_to_have_url(re.compile(r"/auth/(main|login)"))

    @allure.title("UI: форма входа OpenLRS не принимает учётку LMS")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.ui
    @pytest.mark.lrs
    def test_lrs_login_form_rejects_lms_credentials(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Ввести email/пароль админа LMS в форму OpenLRS"):
            lrs = LrsAdminPage(page)
            lrs.open_login_form(env)
            lrs.login_with_form(email, password)

        with allure.step("2. Остаёмся на форме входа — учётки LMS она не принимает"):
            expect(page).to_have_url(re.compile(r"/lrs-admin/login"), timeout=settings.UI_TIMEOUT)
