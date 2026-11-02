"""Часть 3 — синхронизация участников (docs/test_cases/mts_link/04_participants.md).

02.11.2026: сведено с реальным контрактом (живая разведка на mts-link-release-main)
— нет эндпоинта с детализацией по отдельному участнику (личная ссылка), только
агрегированный participants_sync_status; attributes.listeners самого элемента
расписания остаётся пустым массивом даже после успешной сверки (проверено
живьём) — не источник для проверки «кто именно зарегистрирован». Из 6 тестов
оставлен 1: остальные либо требуют разного исхода для разных слушателей
одновременно (непроверяемо без детализации по участнику), либо аудит-лога
запросов (get_request_log_entries, подтверждённо несуществующий эндпоинт, 404),
либо управляемой ошибки от МТС Линк, которую нечем спровоцировать на реальном
проде (нет мока).

register_user() требует, чтобы пользователь был предварительно назначен на поток
(AssignmentsEndpoint.assign) — created_user() сам по себе этого не делает,
регистрация без этого падает 400 "Пользователь не зарегистрирован на поток"
(обнаружено 02.11.2026 при живой проверке)."""
import allure
import pytest

from api.endpoints.assignments import AssignmentsEndpoint


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 3: синхронизация участников")
@pytest.mark.api
@pytest.mark.mts_link
class TestParticipants:
    @allure.title("Первичная регистрация слушателя потока")
    @pytest.mark.smoke
    def test_initial_registration_of_listener(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» только что создано, слушатель назначен на поток."""
        item = created_schedule_item(item_type="mts_link", url="")
        listener = created_user()
        AssignmentsEndpoint(mts_link_endpoint.client).assign(item["program_id"], item["stream_id"], [listener["id"]])
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        assert mts_link_endpoint.wait_for_part_status(item, "participants") == "success"
