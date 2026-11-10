import allure
import pytest


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Негативные сценарии")
class TestUsersNegativeApi:

    @allure.title("POST /admin/user/search с ФИО из двух слов — JSON DataTables, не 500")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_search_user_multiword_returns_data(self, helpdesk_endpoint):
        # До 11.11.2026 — xfail: многословная строка давала 500 ('Undefined array key "data"',
        # UserCrudController.php:82, docs/helpdesk_recon.md §5.1). Исправлено: XPASS на 2066
        # (#121), passed на develop 11.11 — маркер снят, тест стал обычной регрессией.
        data = helpdesk_endpoint.search_user("Фамилия Имя")
        assert isinstance(data, dict) and "data" in data

    @allure.title("GET /admin/user/{несуществующий id}/assign-role — ожидается 404")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_assign_role_not_found(self, helpdesk_endpoint):
        # До 11.11.2026 — xfail: 500 TypeError в RolesRepository::hasOneOfRoles() (контроллер
        # не проверял существование пользователя). Исправлено: 404 на 2066 (#121) и develop.
        client = helpdesk_endpoint.client
        resp = client.session.get(
            f"{client.base_url}{helpdesk_endpoint.USER_PATH}/999999999/assign-role",
            timeout=client.timeout,
        )
        assert resp.status_code == 404, f"Ожидался 404, получено {resp.status_code}: {resp.text[:300]}"
