"""Часть 10 — логирование (docs/test_cases/mts_link/11_logging.md).

12.11.2026: тесты про логирование настроек/токена (test_tenant_settings_change_logged_without_token_value,
test_token_masked_in_request_log_body) убраны — владелец решил не писать токен интеграции тестами вообще
(единственный рабочий на организацию, см. api/endpoints/mts_link.py и удалённый
tests/api/mts_link/test_tenant_settings.py).

Контракт журнала создания/удаления подтверждён curl владельца 12.11.2026 (admin-UI, /admin/logs/changes):
GET /entities-logs?filters[auditable_type]=StreamScheduleItem (не /admin/logs, см. get_action_log) —
test_event_creation_logged/test_event_deletion_logged переписаны под реальную форму записи
(поле "event", не "action") и больше не skip. test_event_update_logged_with_diff_and_sync_flag и
test_all_operations_logged_in_request_log_audit остаются под skip — отдельные, пока не подтверждённые
вопросы (нет поля вида "sync_triggered" в записи лога; /admin/mts-link/request-log-audit подтверждённо 404)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 10: логирование")
@pytest.mark.api
@pytest.mark.mts_link
class TestLogging:
    @allure.title("Создание мероприятия «МТС Линк» логируется")
    @pytest.mark.smoke
    def test_event_creation_logged(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: -."""
        item = created_schedule_item(item_type="mts_link", url="")
        entry = mts_link_endpoint.wait_for_action_logged("schedule_item", item["id"], "created")
        assert entry is not None, "Запись о создании не найдена в журнале"

    @allure.title("Изменение мероприятия логируется с указанием, что менялось и запускалась ли синхронизация")
    @pytest.mark.skip(
        reason="Контракт не подтверждён: entities-logs даёт old_values/new_values (diff), но поля "
        "вида 'sync_triggered' в записи нет — непонятно, как по логу отличить изменение, ушедшее в "
        "МТС Линк, от внутреннего. Нужна отдельная живая разведка."
    )
    def test_event_update_logged_with_diff_and_sync_flag(self, mts_link_endpoint, created_schedule_item):
        """Предусловие: существующее мероприятие «МТС Линк»."""
        item = created_schedule_item(item_type="mts_link", url="")

        mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"name": "Новое название"},
        )
        log = mts_link_endpoint.get_action_log("schedule_item", item["id"])
        synced_entry = next((e for e in log if e.get("event") == "updated"), None)
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

        entry = mts_link_endpoint.wait_for_action_logged("schedule_item", item["id"], "deleted")
        assert entry is not None, "Запись об удалении не найдена в журнале"

    @allure.title("Все запросы/ответы по операциям сохраняются в request_log_audit")
    @pytest.mark.skip(
        reason="/admin/mts-link/request-log-audit подтверждённо 404 (02.11.2026) — это другой контракт, "
        "не entities-logs (там нет request_body/response_body конкретных вызовов в МТС Линк)."
    )
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
