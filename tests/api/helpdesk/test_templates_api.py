import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_template_payload
from tests.api.helpdesk._known_defects import CSRF_TOKEN_DEFECT_REASON


@allure.feature("Хелпдеск: Шаблоны")
@allure.story("CRUD шаблона ответа")
class TestTemplatesApi:

    @allure.title("POST /admin/mail-template — шаблон создаётся и находится в поиске списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_create_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()

        with allure.step("GET /admin/mail-template/search — шаблон найден по наименованию"):
            found = helpdesk_endpoint.find_template_by_name(template["payload"]["name"])
            assert found is not None, f"Шаблон {template['payload']['name']!r} не найден в списке"

    @allure.title("GET /admin/mail-template/{id}/show — карточка шаблона содержит данные созданного шаблона")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_view_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()

        html = helpdesk_endpoint.get_template(template["id"])
        assert template["payload"]["name"] in html
        assert template["payload"]["keywords"] in html

    @allure.title("PUT /admin/mail-template/{id} — наименование шаблона обновляется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_update_template(self, helpdesk_endpoint, created_helpdesk_template):
        template = created_helpdesk_template()
        new_payload = dict(template["payload"])
        new_name = f"{template['payload']['name']}_updated"
        new_payload["name"] = new_name

        with allure.step("PUT /admin/mail-template/{id} с изменённым наименованием"):
            resp = helpdesk_endpoint.update_template(template["id"], new_payload)
            assert resp.status_code < 400, f"Не удалось обновить шаблон: {resp.status_code} {resp.text[:300]}"

        with allure.step("GET /admin/mail-template/{id}/show — наименование обновлено"):
            html = helpdesk_endpoint.get_template(template["id"])
            assert new_name in html

    @allure.title("DELETE /admin/mail-template/{id} — шаблон удаляется и пропадает из списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=CSRF_TOKEN_DEFECT_REASON)
    def test_delete_template(self, helpdesk_endpoint):
        payload = generate_helpdesk_template_payload()
        resp = helpdesk_endpoint.create_template(payload)
        assert resp.status_code < 400, f"Не удалось создать шаблон: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_template_by_name(payload["name"])
        assert found is not None, f"Шаблон {payload['name']!r} не найден перед удалением"
        template_id = found["id"]

        deleted = False
        try:
            with allure.step("DELETE /admin/mail-template/{id}"):
                resp = helpdesk_endpoint.delete_template(template_id)
                assert resp.status_code < 400, f"Не удалось удалить шаблон: {resp.status_code} {resp.text[:300]}"
                deleted = True

            with allure.step("GET /admin/mail-template/search — шаблон не находится в списке"):
                again = helpdesk_endpoint.find_template_by_name(payload["name"])
                assert again is None, "Шаблон всё ещё находится в списке после удаления"
        finally:
            if not deleted:
                try:
                    helpdesk_endpoint.delete_template(template_id)
                except Exception:  # noqa: BLE001 — teardown не должен ронять прогон
                    pass
