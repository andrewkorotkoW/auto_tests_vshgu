"""Часть 0.1 — настройки интеграции тенанта: read-only проверка реального контракта
(docs/test_cases/mts_link/00_tenant_settings.md).

Подтверждено curl владельца 12.11.2026 (admin-UI, вкладка «МТС Линк» в карточке организации):
GET /api/v1/tenants/{tenant_id}/mts_link_config -> 200 {"data": {"masked_token": "***xxxxx",
"is_enabled": true}}. Старый путь /admin/organizations/{id}/mts-link-settings
(tests/api/mts_link/test_tenant_settings.py, @pytest.mark.skip) — 404, не существует.

Только GET: PUT (сохранение токена) здесь не проверяем — это единственный рабочий токен
организации, писать его вслепую нельзя (см. docs/test_cases/mts_link/16_prod_safe_run.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 0.1: настройки интеграции тенанта")
@pytest.mark.api
@pytest.mark.mts_link
class TestTenantConfig:
    @allure.title("Настройки интеграции: включено, токен замаскирован")
    @pytest.mark.smoke
    def test_get_mts_link_config_returns_masked_token_and_enabled(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: тенант с настроенной и включённой интеграцией (единственный прод-аккаунт)."""
        data = mts_link_endpoint.get_tenant_settings(mts_link_tenant_id)

        assert data.get("is_enabled") is True, data
        assert mts_link_endpoint.get_tenant_integration_enabled(mts_link_tenant_id) is True

        token = data.get("masked_token", "")
        assert token, "Ожидалось непустое замаскированное значение токена"
        assert "*" in token, f"Токен должен быть замаскирован: {token!r}"
