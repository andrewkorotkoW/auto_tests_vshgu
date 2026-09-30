"""Часть 2 — синхронизация изменений мероприятия (docs/test_cases/mts_link/03_update.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 2: обновление данных вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestUpdate:
    @allure.title("Изменение полей, уходящих в МТС Линк, запускает синхронизацию")
    @pytest.mark.smoke
    def test_update_synced_fields_triggers_sync(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Изменённое название вебинара"},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.get_part_status(item["id"], "webinar_data") == "in_progress"

        assert mts_link_endpoint.wait_for_part_status(item["id"], "webinar_data") == "success"
        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="update")
        assert audit

    @allure.title("Изменение только внутренних полей не создаёт запроса в МТС Линк")
    def test_update_internal_only_fields_no_request(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        before = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="update")
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"internal_comment": "заметка только для ЛМС"},
        )
        assert resp.status_code == 200, resp.text

        after = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="update")
        assert len(after) == len(before)

    @allure.title("После начала вебинара редактирование заблокировано")
    def test_update_blocked_after_webinar_started(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк», время начала вебинара наступило."""
        item = created_schedule_item(
            item_type="mts_link", url="",
            date_time_from="2020-01-01T10:00", date_time_to="2020-01-01T11:00",
        )
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Попытка изменить начавшийся вебинар"},
        )
        assert resp.status_code in (403, 422), resp.text

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="update")
        assert not audit

    @allure.title("Ошибка обновления: данные ЛМС не откатываются, статус ошибки")
    def test_update_error_keeps_lms_data_sets_error_status(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мок отвечает ошибкой на обновление вебинара."""
        item = created_schedule_item(item_type="mts_link", url="")
        new_name = "Название при ошибке мока"
        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": new_name},
        )
        assert resp.status_code == 200, resp.text

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert fetched["attributes"]["name"] == new_name

        assert mts_link_endpoint.wait_for_part_status(item["id"], "webinar_data") == "error"

    @allure.title("Ошибка обновления → автоматический ретрай")
    def test_update_error_triggers_auto_retry(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: мок сначала отвечает ошибкой, затем успехом."""
        item = created_schedule_item(item_type="mts_link", url="")
        mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Название с временной ошибкой мока"},
        )
        assert mts_link_endpoint.get_part_status(item["id"], "webinar_data") == "error"
        assert mts_link_endpoint.wait_for_part_status(item["id"], "webinar_data", timeout=120.0) == "success"
