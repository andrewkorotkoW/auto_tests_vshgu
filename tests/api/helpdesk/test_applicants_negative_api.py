import allure
import pytest


@allure.feature("Хелпдеск: Заявители")
@allure.story("Негативные сценарии")
class TestApplicantsNegativeApi:

    @allure.title("POST /admin/identity без обязательных полей — ожидается 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_applicant_missing_required_fields(self, helpdesk_endpoint):
        resp = helpdesk_endpoint.add_applicant({})
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text[:300]}"
