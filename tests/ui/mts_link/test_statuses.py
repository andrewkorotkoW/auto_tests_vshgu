"""Часть 7 — статусы интеграции и уведомления (docs/test_cases/mts_link/08_statuses.md)."""
import allure
import pytest

from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 7: статусы интеграции и уведомления")
@pytest.mark.ui
@pytest.mark.mts_link
class TestStatuses:
    def _open_card(self, admin_event_mts_page, item):
        admin_event_mts_page.open(
            settings.UI_BASE_URL, item["program_id"], item["stream_id"], item["module_id"], item["id"]
        )

    @allure.title("Сводный статус «Ошибка», если хотя бы одна часть завершилась ошибкой")
    @pytest.mark.smoke
    def test_summary_status_error_if_any_part_failed(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: мероприятие «МТС Линк», у которого часть «Файлы презентаций» в
        статусе «Ошибка», остальные — «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        self._open_card(admin_event_mts_page, item)
        assert "ошибк" in admin_event_mts_page.summary_status_text().lower()

    @allure.title("Сводный статус «В процессе», пока хоть одна часть выполняется")
    def test_summary_status_in_progress_while_any_part_running(self, admin_event_mts_page, created_schedule_item):
        """Предусловие: часть «Участники» в статусе «В процессе», остальные не завершены/успешны."""
        item = created_schedule_item(item_type="mts_link", url="")
        self._open_card(admin_event_mts_page, item)
        assert "процесс" in admin_event_mts_page.summary_status_text().lower()

    @allure.title("Сводный статус «Успешно», когда все части успешны")
    def test_summary_status_success_when_all_parts_succeeded(self, admin_event_mts_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: все 5 частей синхронизации завершены успешно."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_summary_status(item["id"], timeout=90.0) == "success"
        self._open_card(admin_event_mts_page, item)
        assert "успешно" in admin_event_mts_page.summary_status_text().lower()

    @allure.title("Индикатор состояния в списке мероприятий")
    def test_status_indicator_in_events_list(self, admin_event_mts_page, created_schedule_item, admin_page):
        """Предусловие: мероприятия с разными сводными статусами (успех/ошибка/в процессе)."""
        item = created_schedule_item(item_type="mts_link", url="")
        admin_page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
            f"/modules/{item['module_id']}"
        )
        indicator = admin_event_mts_page.status_indicator_in_list(item["name"])
        assert indicator.is_visible(timeout=settings.UI_TIMEOUT)

    @allure.title("Индикатор состояния в календаре")
    def test_status_indicator_in_calendar(self, admin_event_mts_page, created_schedule_item, admin_page):
        """Предусловие: мероприятие «МТС Линк» со статусом «Ошибка интеграции»."""
        item = created_schedule_item(item_type="mts_link", url="")
        admin_page.goto(f"{settings.UI_BASE_URL}/admin/calendar")
        indicator = admin_event_mts_page.status_indicator_in_calendar(item["name"])
        assert indicator.is_visible(timeout=settings.UI_TIMEOUT)

    @allure.title("Детализация по пяти частям в карточке")
    def test_card_shows_per_part_status_breakdown(self, admin_event_mts_page, created_schedule_item):
        """Предусловие: мероприятие «МТС Линк» с разными статусами по частям."""
        item = created_schedule_item(item_type="mts_link", url="")
        self._open_card(admin_event_mts_page, item)
        for part in ("creation", "webinar_data", "participants", "lecturers", "files"):
            assert admin_event_mts_page.part_status_text(part)

    @allure.title("Пуш отправляется один раз на факт ошибки, не на каждый ретрай")
    def test_push_sent_once_per_error_not_per_retry(self, mts_link_endpoint, created_schedule_item, api_client):
        """Предусловие: мероприятие уходит в ошибку, затем несколько авторетраев подряд
        тоже завершаются ошибкой."""
        from api.endpoints.notifications import NotificationsEndpoint

        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation", timeout=90.0) == "error"

        notifications_endpoint = NotificationsEndpoint(api_client)
        notifications = notifications_endpoint.list()
        related = [
            n for n in notifications
            if str(item["id"]) in str(n.get("attributes", {}).get("text", ""))
        ]
        assert len(related) == 1, related

    @allure.title("Переход по пушу открывает карточку мероприятия")
    def test_push_navigates_to_event_card(self, user_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: пуш об ошибке интеграции получен."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation", timeout=90.0) == "error"

        user_page.goto(f"{settings.UI_BASE_URL}/notifications")
        push = user_page.locator(f"[data-qa='notification-item']", has_text=item["name"]).first
        push.click(timeout=settings.UI_TIMEOUT)
        user_page.wait_for_url(
            f"**/programs/{item['program_id']}/streams/{item['stream_id']}"
            f"/modules/{item['module_id']}/schedule-items/{item['id']}"
        )
