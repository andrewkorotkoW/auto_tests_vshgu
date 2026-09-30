"""Регресс: появление типа «МТС Линк» не ломает обычные очные мероприятия
(docs/test_cases/mts_link/15_regression.md)."""
import allure
import pytest

from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Регресс существующего функционала")
@pytest.mark.ui
@pytest.mark.mts_link
class TestRegression:
    @allure.title("Обычное мероприятие создаётся как раньше")
    @pytest.mark.smoke
    def test_regular_event_creation_unchanged(self, admin_event_mts_page, created_module, mts_link_endpoint):
        """Предусловие: тенант с настроенной интеграцией МТС Линк (появление нового типа
        не должно ломать обычный)."""
        module = created_module()
        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, module["program_id"], module["stream_id"], module["id"]
        )
        assert admin_event_mts_page.is_url_field_disabled() is False

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=module["id"])
        assert not audit

    @allure.title("Обычное мероприятие редактируется как раньше")
    def test_regular_event_editing_unchanged(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: существующее обычное очное мероприятие."""
        item = created_schedule_item(item_type="webinar")
        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )
        assert admin_event_mts_page.is_url_field_disabled() is False

        audit = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"])
        assert not audit

    @allure.title("Таблица слушателей для обычных мероприятий не меняется")
    def test_regular_events_listeners_table_unchanged(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: поток с обычными очными мероприятиями (без типа «МТС Линк»)."""
        listener = created_user()
        item = created_schedule_item(item_type="webinar")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        stream_listeners_page.page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
        )
        stream_listeners_page.open_listeners_tab()
        text = stream_listeners_page.attendance_cell_text(listener["id"], item["id"])
        assert "%" not in text

    @allure.title("Тенант без интеграции: тип «МТС Линк» недоступен, остальное не меняется")
    def test_tenant_without_integration_unaffected(self, admin_event_mts_page, created_module):
        """Предусловие: сид части 12 — тенант без интеграции с МТС Линк."""
        module = created_module()
        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, module["program_id"], module["stream_id"], module["id"]
        )
        assert admin_event_mts_page.is_mts_link_type_option_visible() is False
