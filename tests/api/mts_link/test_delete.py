"""Часть 6 — удаление вебинара (docs/test_cases/mts_link/07_delete.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 6: удаление вебинара")
@pytest.mark.api
@pytest.mark.mts_link
class TestDelete:
    @allure.title("Удаление сразу в ЛМС")
    @pytest.mark.smoke
    def test_delete_event_immediately_in_lms(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        deleted = schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        assert deleted is True

    @allure.title("Фоном удаляются вебинар и сессия")
    def test_background_deletion_removes_webinar_and_session(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно» удалено в ЛМС."""
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])

        entries = mts_link_endpoint.wait_for_deletion(item["id"])
        operations = {e.get("entity") for e in entries if e.get("success")}
        assert {"webinar", "session"}.issubset(operations), entries

    @allure.title("Регистрации/лекторы/файлы удаляются вместе с вебинаром")
    def test_related_entities_removed_with_webinar_no_separate_calls(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие с зарегистрированными слушателями, лекторами и файлами."""
        listener = created_user()
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        schedule_items_endpoint.register_user(item["id"], listener["id"])
        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"

        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        mts_link_endpoint.wait_for_deletion(item["id"])

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])
        separate_removal_ops = {"remove_participant", "remove_lecturer", "detach_file"}
        assert not any(e.get("operation") in separate_removal_ops for e in audit), audit

    @allure.title("Ошибка удаления → автоматический ретрай")
    def test_deletion_error_triggers_auto_retry(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мок отвечает ошибкой на удаление, затем успехом."""
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])

        entries = mts_link_endpoint.wait_for_deletion(item["id"], timeout=120.0)
        assert any(e.get("success") for e in entries), entries

    @allure.title("После успешного ретрая не остаётся «висящих» объектов")
    def test_no_hanging_objects_after_successful_retry(
        self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint
    ):
        """Предусловие: сценарий TC-MTS-045 доведён до успешного завершения."""
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        entries = mts_link_endpoint.wait_for_deletion(item["id"], timeout=120.0)

        final_entries = {e.get("entity"): e for e in entries if e.get("success")}
        assert final_entries.get("webinar")
        assert final_entries.get("session")
