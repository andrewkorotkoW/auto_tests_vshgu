"""Часть 0.1 — настройка интеграции в карточке тенанта (docs/test_cases/mts_link/00_tenant_settings.md).

Тело тестов — предполагаемый контракт api/endpoints/mts_link.py (get/save_tenant_settings),
реально выполнится только при MTS_LINK_READY=1 (см. conftest.py:skip_if_mts_link_not_ready).
"""
import allure
import pytest

from utils.logger import logger


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 0.1: настройки интеграции тенанта")
@pytest.mark.api
@pytest.mark.mts_link
class TestTenantSettings:
    @allure.title("Сохранение с валидным токеном → интеграция настроена и проверена")
    @pytest.mark.smoke
    def test_save_valid_token_marks_integration_configured(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: сид части 12 — тенант без интеграции, мок валидирует токен успешно."""
        with allure.step("PUT настроек с валидным токеном"):
            resp = mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token="valid-token")
            assert resp.status_code == 200, resp.text

        with allure.step("GET настроек тенанта"):
            assert mts_link_endpoint.get_tenant_integration_enabled(mts_link_tenant_id) is True

    @allure.title("Невалидный токен → настройки не сохраняются, понятная ошибка")
    def test_save_invalid_token_not_saved(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: мок отвечает 401 на проверку токена."""
        resp = mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token="invalid-token")
        assert resp.status_code in (400, 422), resp.text
        assert resp.json().get("errors"), "В ответе должно быть понятное сообщение об ошибке"
        assert mts_link_endpoint.get_tenant_integration_enabled(mts_link_tenant_id) is False

    @allure.title("МТС Линк недоступен при сохранении → настройки не сохраняются")
    def test_save_when_mts_unavailable_not_saved(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: мок отвечает недоступностью сервиса (503/timeout)."""
        resp = mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token="any-token")
        assert resp.status_code >= 400, resp.text
        before = mts_link_endpoint.get_tenant_settings(mts_link_tenant_id)
        assert not before.get("attributes", {}).get("integration_configured")

    @allure.title("Токен в ответе всегда замаскирован")
    def test_get_settings_returns_masked_token(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: тенант с настроенной и проверенной интеграцией."""
        data = mts_link_endpoint.get_tenant_settings(mts_link_tenant_id)
        token = data.get("attributes", {}).get("token", "")
        assert token, "Ожидается замаскированное значение токена, а не пусто"
        assert "*" in token, "Токен должен быть замаскирован"

    @allure.title("Поле токена не тронули при сохранении → токен остаётся прежним")
    def test_save_without_touching_token_keeps_previous_value(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: тенант с настроенной интеграцией. token=None — поле не передаётся
        в payload вовсе (save_tenant_settings трактует так), не пустой строкой."""
        resp = mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token=None, default_meeting_settings={})
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.get_tenant_integration_enabled(mts_link_tenant_id) is True

    @allure.title("Новое значение токена заменяет прежнее целиком")
    def test_save_new_token_replaces_previous_fully(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: тенант с настроенной интеграцией, новое валидное значение токена."""
        resp = mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token="brand-new-token")
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.get_tenant_integration_enabled(mts_link_tenant_id) is True
        logger.info("Мок должен зафиксировать новое значение токена целиком — сверяется на стороне мока")

    @allure.title("Права на редактирование: admin/tenant-admin сохраняют, manager — 403")
    def test_save_settings_role_permissions(self, env, mts_link_tenant_id):
        """Предусловие: -. Роли admin/tenant_admin/manager — через разные сессии env
        (config/environments.get_session, учётки DEVELOP_TENANT_ADMIN_LOGIN/PASSWORD и
        DEVELOP_MANAGER_LOGIN/PASSWORD в .env — см. план, п.4, «учётки admin/tenant-admin/
        manager/teacher/learner»; если не заданы, откатываются на дефолтную учётку —
        тест тогда не различит роли, это ограничение окружения, а не теста)."""
        from api.client import ApiClient
        from api.endpoints.mts_link import MtsLinkEndpoint
        from config.environments import get_session

        for role, expected_status in (("admin", 200), ("tenant_admin", 200), ("manager", 403)):
            session = get_session(env, role=role)
            client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)
            endpoint = MtsLinkEndpoint(client)
            resp = endpoint.save_tenant_settings(mts_link_tenant_id, token="role-check-token")
            assert resp.status_code == expected_status, f"{role}: ожидался {expected_status}, получили {resp.status_code}"
