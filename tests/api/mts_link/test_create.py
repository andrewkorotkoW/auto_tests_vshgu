"""Часть 1 — фоновое создание вебинара при создании мероприятия (docs/test_cases/mts_link/02_create.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 1: создание вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestCreate:
    @allure.title("Мероприятие создаётся в ЛМС сразу, не дожидаясь МТС Линк")
    @pytest.mark.smoke
    def test_event_created_immediately_status_in_progress(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: тенант с интеграцией; мок отвечает на создание вебинара с задержкой."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert item["id"] is not None

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["id"] == item["id"]

        status = mts_link_endpoint.get_part_status(item["id"], "creation")
        assert status == "in_progress", status

    @allure.title("Фоновое создание вебинара завершилось успешно")
    def test_event_creation_success_saves_ids_and_url(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мок отвечает успешным созданием сессии и вебинара."""
        item = created_schedule_item(item_type="mts_link", url="")

        status = mts_link_endpoint.wait_for_part_status(item["id"], "creation")
        assert status == "success", status

        data = mts_link_endpoint.get_event_integration_data(item["id"])
        assert data.get("webinar_id")
        assert data.get("session_id")
        assert data.get("url")

    @allure.title("Ошибка создания вебинара → мероприятие остаётся, URL пуст")
    def test_event_creation_error_keeps_event_empty_url(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мок отвечает ошибкой на создание сессии/вебинара."""
        item = created_schedule_item(item_type="mts_link", url="")

        status = mts_link_endpoint.wait_for_part_status(item["id"], "creation")
        assert status == "error", status

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"].get("url") in (None, "")

    @allure.title("Ошибка создания → автоматический ретрай")
    def test_event_creation_error_triggers_auto_retry(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мок сначала отвечает ошибкой, затем успехом."""
        item = created_schedule_item(item_type="mts_link", url="")

        first_status = mts_link_endpoint.get_part_status(item["id"], "creation")
        assert first_status in ("in_progress", "error"), first_status

        final_status = mts_link_endpoint.wait_for_part_status(item["id"], "creation", timeout=120.0)
        assert final_status == "success", final_status
        data = mts_link_endpoint.get_event_integration_data(item["id"])
        assert data.get("webinar_id")
        assert data.get("url")

    @allure.title("Части 2–5 не стартуют, пока вебинар не создан")
    def test_other_parts_not_started_before_webinar_created(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мок держит создание вебинара в незавершённом/ошибочном состоянии."""
        item = created_schedule_item(item_type="mts_link", url="")
        listener = created_user()
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        status = mts_link_endpoint.get_integration_status(item["id"])
        assert status.get("parts", {}).get("creation") != "success"
        for part in ("participants", "lecturers", "files"):
            assert status.get("parts", {}).get(part) in (None, "not_started"), (part, status)

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])
        assert not any(e.get("operation") in ("register_participant", "attach_file") for e in audit)
