import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_group_payload
from tests.api.helpdesk._known_defects import GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON


@allure.feature("Хелпдеск: Группы")
@allure.story("CRUD группы")
class TestGroupsApi:

    @allure.title("POST /admin/group — группа создаётся и находится в поиске списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON)
    def test_create_group(self, helpdesk_endpoint, created_helpdesk_group):
        group = created_helpdesk_group()

        with allure.step("GET /admin/group/search — группа найдена по названию"):
            found = helpdesk_endpoint.find_group_by_name(group["payload"]["name"])
            assert found is not None, f"Группа {group['payload']['name']!r} не найдена в списке"

    @allure.title("GET /admin/group/{id}/show — карточка группы содержит данные созданной группы")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON)
    def test_view_group(self, helpdesk_endpoint, created_helpdesk_group):
        group = created_helpdesk_group()

        html = helpdesk_endpoint.get_group(group["id"])
        assert group["payload"]["name"] in html
        assert group["payload"]["prefix"] in html
        assert group["payload"]["email"] in html

    @allure.title("PUT /admin/group/{id} — название группы обновляется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON)
    def test_update_group(self, helpdesk_endpoint, created_helpdesk_group):
        group = created_helpdesk_group()
        new_payload = dict(group["payload"])
        new_name = f"{group['payload']['name']}_updated"
        new_payload["name"] = new_name

        with allure.step("PUT /admin/group/{id} с изменённым названием"):
            resp = helpdesk_endpoint.update_group(group["id"], new_payload)
            assert resp.status_code < 400, f"Не удалось обновить группу: {resp.status_code} {resp.text[:300]}"

        with allure.step("GET /admin/group/{id}/show — название обновлено"):
            html = helpdesk_endpoint.get_group(group["id"])
            assert new_name in html

    @allure.title("DELETE /admin/group/{id} — группа удаляется и пропадает из списка")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(strict=False, reason=GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON)
    def test_delete_group(self, helpdesk_endpoint):
        payload = generate_helpdesk_group_payload()
        resp = helpdesk_endpoint.create_group(payload)
        assert resp.status_code < 400, f"Не удалось создать группу: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_group_by_name(payload["name"])
        assert found is not None, f"Группа {payload['name']!r} не найдена перед удалением"
        group_id = found["id"]

        deleted = False
        try:
            with allure.step("DELETE /admin/group/{id}"):
                resp = helpdesk_endpoint.delete_group(group_id)
                assert resp.status_code < 400, f"Не удалось удалить группу: {resp.status_code} {resp.text[:300]}"
                deleted = True

            with allure.step("GET /admin/group/search — группа не находится в списке"):
                again = helpdesk_endpoint.find_group_by_name(payload["name"])
                assert again is None, "Группа всё ещё находится в списке после удаления"
        finally:
            if not deleted:
                try:
                    helpdesk_endpoint.delete_group(group_id)
                except Exception:  # noqa: BLE001 — teardown не должен ронять прогон
                    pass
