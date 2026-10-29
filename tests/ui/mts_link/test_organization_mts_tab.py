"""Вкладка «МТС Линк» в карточке организации — только отображение, никаких реальных
вызовов в МТС Линк (не сохраняет токен, не меняет переключатель).

Подтверждено живой разведкой на стенде mts-link-release-main 29.10.2026 —
ui/pages/admin_tenant_page.py. Тенант берётся из MTS_LINK_TENANT_ID (.env) — та же
переменная, что уже заведена под этот пакет тестов (см. conftest.py).
"""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Карточка организации: вкладка «МТС Линк»")
class TestOrganizationMtsTab:

    @allure.title("UI: Администратор видит вкладку «МТС Линк» со статусом интеграции")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.mts_link
    def test_admin_sees_mts_link_tab(self, admin_tenant_page, env, mts_link_tenant_id):
        with allure.step("1. Открыть карточку организации"):
            admin_tenant_page.open(env.ui_base_url, mts_link_tenant_id)

        with allure.step("2. Вкладка «МТС Линк» видна роли admin"):
            assert admin_tenant_page.is_mts_link_tab_visible(), "Вкладка «МТС Линк» не видна администратору"
            admin_tenant_page.open_mts_link_tab()

        with allure.step("3. Статус интеграции отображается"):
            status_text = admin_tenant_page.integration_status_text()
            assert status_text, "Статус интеграции не отображается"
            allure.attach(status_text, name="integration_status", attachment_type=allure.attachment_type.TEXT)

        with allure.step("4. Токен в поле замаскирован — не читаем значение, только что оно не пустое"):
            placeholder = admin_tenant_page.masked_token_placeholder()
            assert placeholder.startswith("***"), f"Плейсхолдер токена не замаскирован: {placeholder!r}"
