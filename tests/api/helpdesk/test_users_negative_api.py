import allure
import pytest


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Негативные сценарии")
class TestUsersNegativeApi:

    @allure.title("POST /admin/user/search с ФИО из двух слов — известный дефект (HTTP 500)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        strict=False,
        reason='Известный дефект: POST /admin/user/search с многословной строкой кидает 500 '
        '(Undefined array key "data", UserCrudController.php:82) — см. docs/helpdesk_recon.md §5.1',
    )
    def test_search_user_multiword_returns_500_known_defect(self, helpdesk_endpoint):
        data = helpdesk_endpoint.search_user("Фамилия Имя")
        assert isinstance(data, dict) and "data" in data

    @allure.title("GET /admin/user/{несуществующий id}/assign-role — ожидается 404")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        strict=False,
        reason="Фактический код — 500 (TypeError: Lms\\Repositories\\RolesRepository::hasOneOfRoles(): "
        "Argument #1 ($user) must be of type Lms\\Models\\User, null given — UserCrudController.php:252), "
        "а не 404: контроллер не проверяет существование пользователя до вызова hasOneOfRoles(). "
        "Кандидат в дефект, воспроизведено стабильно.",
    )
    def test_assign_role_not_found(self, helpdesk_endpoint):
        client = helpdesk_endpoint.client
        resp = client.session.get(
            f"{client.base_url}{helpdesk_endpoint.USER_PATH}/999999999/assign-role",
            timeout=client.timeout,
        )
        assert resp.status_code == 404, f"Ожидался 404, получено {resp.status_code}: {resp.text[:300]}"
