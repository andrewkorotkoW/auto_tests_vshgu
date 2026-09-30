"""Часть 0 — новый тип мероприятия «МТС Линк» (docs/test_cases/mts_link/01_event_type.md).

UI-проверки поверх AdminEventMtsPage/AdminTenantPage — реально выполнятся только при
MTS_LINK_READY=1 (см. conftest.py:skip_if_mts_link_not_ready).
"""
import allure
import pytest

from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 0: тип мероприятия «МТС Линк»")
@pytest.mark.ui
@pytest.mark.mts_link
class TestEventType:
    @allure.title("Иконка типа «МТС Линк» видна при настроенной интеграции")
    def test_type_icon_visible_when_integration_configured(
        self, admin_event_mts_page, created_module, mts_link_tenant_id
    ):
        """Предусловие: сид части 12 — тенант с настроенной и проверенной интеграцией."""
        module = created_module()
        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, module["program_id"], module["stream_id"], module["id"]
        )
        assert admin_event_mts_page.is_mts_link_type_option_visible() is True

    @allure.title("Иконка скрыта без интеграции или при непроверенной")
    def test_type_icon_hidden_without_integration(self, admin_event_mts_page, created_module):
        """Предусловие: сид части 12 — тенант без интеграции с МТС Линк."""
        module = created_module()
        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, module["program_id"], module["stream_id"], module["id"]
        )
        assert admin_event_mts_page.is_mts_link_type_option_visible() is False

    @allure.title("URL мероприятия недоступен для заполнения в форме создания")
    def test_url_field_disabled_on_create(self, admin_event_mts_page, created_module):
        """Предусловие: тенант с настроенной интеграцией."""
        module = created_module()
        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, module["program_id"], module["stream_id"], module["id"]
        )
        admin_event_mts_page.select_mts_link_type()
        assert admin_event_mts_page.is_url_field_disabled() is True

    @allure.title("Тип мероприятия нельзя сменить с обычного на «МТС Линк»")
    def test_cannot_change_type_to_mts_link_after_create(self, admin_event_mts_page, created_schedule_item):
        """Предусловие: существующее обычное очное мероприятие."""
        item = created_schedule_item(item_type="webinar")
        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )
        assert admin_event_mts_page.is_type_field_editable() is False

    @allure.title("Тип мероприятия нельзя сменить с «МТС Линк» на обычный")
    def test_cannot_change_type_from_mts_link_after_create(self, admin_event_mts_page, created_schedule_item):
        """Предусловие: существующее мероприятие типа «МТС Линк»."""
        item = created_schedule_item(item_type="mts_link", url="")
        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )
        assert admin_event_mts_page.is_type_field_editable() is False

    @allure.title("В «Результатах активности» отображаются статусы создания вебинара и конвертации записи")
    def test_activity_results_show_mts_statuses(self, user_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: мероприятие «МТС Линк» с известными статусами (создание вебинара
        «в процессе», запись «конвертируется»). «Результаты активности» как отдельная
        страница в page objects репозитория не выделена (узел карты продукта не заведён,
        см. tests/product_map.yml) — судя по остальным методам ActivityPage, это та же
        страница, где слушатель завершает мероприятие. TODO: уточнить маршрут после
        появления ветки — здесь используется расширение ui/pages/activity_page.py
        (recording_player) как единственная точка входа, которая уже есть."""
        from ui.pages.activity_page import ActivityPage

        item = created_schedule_item(item_type="mts_link", url="")
        status = mts_link_endpoint.get_part_status(item["id"], "creation")
        assert status == "in_progress", status

        activity_page = ActivityPage(user_page)
        assert activity_page.is_recording_player_visible() is False, (
            "Пока запись конвертируется, плеер ещё не должен быть доступен"
        )

    @allure.title("Отключение интеграции: старые мероприятия «МТС Линк» продолжают работать")
    def test_disable_integration_keeps_existing_events_working(
        self, admin_tenant_page, admin_event_mts_page, created_schedule_item, mts_link_tenant_id
    ):
        """Предусловие: тенант с интеграцией и существующим мероприятием «МТС Линк»."""
        item = created_schedule_item(item_type="mts_link", url="")

        admin_tenant_page.open(settings.UI_BASE_URL, mts_link_tenant_id)
        admin_tenant_page.open_integrations_tab()
        assert admin_tenant_page.integration_configured_badge_visible() is False

        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )
        assert admin_event_mts_page.type_icon().is_visible(timeout=5000)

        admin_event_mts_page.open_create_form(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"]
        )
        assert admin_event_mts_page.is_mts_link_type_option_visible() is False
