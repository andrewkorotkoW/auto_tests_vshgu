import allure
import pytest

from tests.api.helpdesk._known_defects import CSRF_TOKEN_DEFECT_REASON


@allure.feature("Хелпдеск: Группы")
@allure.story("Негативные сценарии")
class TestGroupsNegativeApi:

    @allure.title("POST /admin/group без обязательных полей — ожидается 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_create_group_missing_required_fields(self, helpdesk_endpoint):
        resp = helpdesk_endpoint.create_group({})
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text[:300]}"

    @allure.title("POST /admin/group от пользователя без доступа к Helpdesk — ожидается 403")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        strict=False,
        reason="user_session и admin_session из корневого conftest.py на develop резолвятся в один "
        "и тот же аккаунт (id=3, подтверждено GET /auth/me для обеих сессий) — отдельного тестового "
        "пользователя без доступа к Helpdesk через эти фикстуры получить нельзя. Запрос реально уходит "
        "от администратора и получает 422 (валидационная ошибка, как у admin), а не 403.",
    )
    def test_create_group_forbidden_for_non_admin(self, user_helpdesk_endpoint):
        client = user_helpdesk_endpoint.client
        resp = client.session.post(
            f"{client.base_url}{user_helpdesk_endpoint.GROUP_PATH}",
            data={},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=client.timeout,
        )
        assert resp.status_code == 403, f"Ожидался 403, получено {resp.status_code}: {resp.text[:300]}"

    @allure.title("GET /admin/group/{несуществующий id}/edit — ожидается 404")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_edit_group_not_found(self, helpdesk_endpoint):
        client = helpdesk_endpoint.client
        resp = client.session.get(
            f"{client.base_url}{helpdesk_endpoint.GROUP_PATH}/999999999/edit",
            timeout=client.timeout,
        )
        assert resp.status_code == 404, f"Ожидался 404, получено {resp.status_code}: {resp.text[:300]}"
