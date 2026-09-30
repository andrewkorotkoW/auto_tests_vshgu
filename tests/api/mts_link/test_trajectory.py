"""Часть 14 — вебинар в индивидуальной траектории (docs/test_cases/mts_link/13_trajectory.md).

Индивидуальная траектория (ИТ) — назначение слушателю вне стандартного потока; выделенного
API для этого в клиенте репозитория нет, ближайшая существующая фикстура —
`assigned_user`/`assignments_endpoint` (назначение в поток). Контракт назначения именно в ИТ
не подтверждён — см. docstring api/endpoints/mts_link.py: get_it_webinar.
"""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 14: вебинар в индивидуальной траектории")
@pytest.mark.api
@pytest.mark.mts_link
class TestTrajectory:
    @allure.title("Назначение в ИТ создаёт отдельный вебинар")
    @pytest.mark.smoke
    def test_it_assignment_creates_dedicated_webinar(self, mts_link_endpoint, assigned_user, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк» назначено слушателю в индивидуальной траектории."""
        assignment = assigned_user()
        item = created_schedule_item(item_type="mts_link", url="")

        webinar = mts_link_endpoint.get_it_webinar(assignment["user"]["id"])
        assert webinar.get("webinar_id")
        event_webinar = mts_link_endpoint.get_event_integration_data(item["id"])
        assert webinar.get("webinar_id") != event_webinar.get("webinar_id")

    @allure.title("На вебинар в ИТ регистрируется только этот слушатель")
    def test_it_webinar_has_single_registered_listener(self, mts_link_endpoint, assigned_user):
        """Предусловие: вебинар под назначение в ИТ создан."""
        assignment = assigned_user()
        webinar = mts_link_endpoint.get_it_webinar(assignment["user"]["id"])
        participants = webinar.get("participants", [])
        assert len(participants) == 1
        assert participants[0].get("user_id") == assignment["user"]["id"]

    @allure.title("Снятие назначения до вебинара удаляет его целиком")
    def test_removing_it_assignment_before_webinar_deletes_it(self, mts_link_endpoint, assigned_user):
        """Предусловие: назначение в ИТ с созданным, ещё не проведённым вебинаром."""
        from api.endpoints.assignments import AssignmentsEndpoint

        assignment = assigned_user()
        webinar = mts_link_endpoint.get_it_webinar(assignment["user"]["id"])

        assignments_endpoint = AssignmentsEndpoint(mts_link_endpoint.client)
        assignments_endpoint.assign(
            assignment["stream"]["program_id"], assignment["stream"]["id"], []
        )
        entries = mts_link_endpoint.wait_for_deletion(webinar["webinar_id"])
        assert any(e.get("success") for e in entries), entries

    @allure.title("Снятие назначения после вебинара не удаляет его")
    def test_removing_it_assignment_after_webinar_keeps_it(self, mts_link_endpoint, assigned_user):
        """Предусловие: назначение в ИТ, вебинар уже прошёл, есть статистика посещения."""
        from api.endpoints.assignments import AssignmentsEndpoint

        assignment = assigned_user()
        webinar = mts_link_endpoint.get_it_webinar(assignment["user"]["id"])

        assignments_endpoint = AssignmentsEndpoint(mts_link_endpoint.client)
        assignments_endpoint.assign(
            assignment["stream"]["program_id"], assignment["stream"]["id"], []
        )
        entries = mts_link_endpoint.get_request_log_entries(operation="delete")
        assert not any(e.get("entity") == "webinar" and e.get("entity_id") == webinar["webinar_id"] for e in entries)
