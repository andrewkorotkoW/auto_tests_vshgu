"""Часть 10 — логирование (docs/test_cases/mts_link/11_logging.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 10: логирование")
@pytest.mark.api
@pytest.mark.mts_link
class TestLogging:
    @allure.title("Изменение настроек тенанта логируется без значения токена")
    @pytest.mark.smoke
    def test_tenant_settings_change_logged_without_token_value(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: тенант с интеграцией."""
        mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token="new-logged-token")

        log = mts_link_endpoint.get_action_log("organization", mts_link_tenant_id)
        assert log, "Ожидалась запись об изменении настроек"
        entry = log[0]
        assert "new-logged-token" not in str(entry)

    @allure.title("Создание мероприятия «МТС Линк» логируется")
    def test_event_creation_logged(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: -."""
        item = created_schedule_item(item_type="mts_link", url="")
        log = mts_link_endpoint.get_action_log("schedule_item", item["id"])
        assert any(e.get("action") == "create" for e in log), log

    @allure.title("Изменение мероприятия логируется с указанием, что менялось и запускалась ли синхронизация")
    def test_event_update_logged_with_diff_and_sync_flag(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: существующее мероприятие «МТС Линк»."""
        item = created_schedule_item(item_type="mts_link", url="")

        mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Новое название"},
        )
        log = mts_link_endpoint.get_action_log("schedule_item", item["id"])
        synced_entry = next((e for e in log if e.get("action") == "update"), None)
        assert synced_entry is not None and synced_entry.get("sync_triggered") is True

        mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"internal_comment": "только для ЛМС"},
        )
        log = mts_link_endpoint.get_action_log("schedule_item", item["id"])
        internal_entry = log[0]
        assert internal_entry.get("sync_triggered") is False

    @allure.title("Удаление мероприятия логируется")
    def test_event_deletion_logged(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: существующее мероприятие «МТС Линк»."""
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])

        log = mts_link_endpoint.get_action_log("schedule_item", item["id"])
        assert any(e.get("action") == "delete" for e in log), log

    @allure.title("Все запросы/ответы по операциям сохраняются в request_log_audit")
    def test_all_operations_logged_in_request_log_audit(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие проходит полный цикл операций: создание, обновление,
        участники, лекторы, файлы, удаление."""
        listener = created_user()
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        schedule_items_endpoint.register_user(item["id"], listener["id"])
        mts_link_endpoint.attach_file(
            item["program_id"], item["stream_id"], item["module_id"], item["id"], "test_data/certificat.pdf"
        )
        mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"], attributes={"name": "Изменено"}
        )
        schedule_items_endpoint.delete(item["program_id"], item["stream_id"], item["module_id"], item["id"])

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])
        operations = {e.get("operation") for e in audit}
        expected = {"create", "update", "register_participant", "add_lecturer", "upload_file", "delete"}
        assert expected.issubset(operations), operations
        for entry in audit:
            assert "request_body" in entry and "response_body" in entry and "success" in entry

    @allure.title("Токен маскируется в теле запроса в логе")
    def test_token_masked_in_request_log_body(self, mts_link_endpoint, mts_link_tenant_id):
        """Предусловие: операция, где в теле/заголовке запроса к МТС Линк фигурирует токен."""
        secret_token = "very-secret-mts-link-token"
        mts_link_endpoint.save_tenant_settings(mts_link_tenant_id, token=secret_token)

        entries = mts_link_endpoint.get_request_log_entries(operation="settings_update")
        assert entries
        for entry in entries:
            assert secret_token not in str(entry.get("request_body", ""))
