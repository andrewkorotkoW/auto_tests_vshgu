import allure
import pytest


@allure.feature("Хелпдеск: Шаблоны")
@allure.story("Негативные сценарии")
class TestTemplatesNegativeApi:

    @allure.title("POST /admin/mail-template без обязательных полей — ожидается 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_template_missing_required_fields(self, helpdesk_endpoint):
        resp = helpdesk_endpoint.create_template({})
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text[:300]}"

    @allure.title("GET /admin/mail-template/{несуществующий id}/edit — ожидается 404")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_edit_template_not_found(self, helpdesk_endpoint):
        client = helpdesk_endpoint.client
        resp = client.session.get(
            f"{client.base_url}{helpdesk_endpoint.TEMPLATE_PATH}/999999999/edit",
            timeout=client.timeout,
        )
        assert resp.status_code == 404, f"Ожидался 404, получено {resp.status_code}: {resp.text[:300]}"
