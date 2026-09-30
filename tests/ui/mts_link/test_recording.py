"""Часть 11 — запись вебинара в результатах активности (docs/test_cases/mts_link/12_recording.md).

«Результаты активности» как отдельная страница/page object не выделены в репозитории —
см. точечное расширение ui/pages/activity_page.py (recording_player/play_recording_to_end)
и продуктовую карту tests/product_map.yml. TODO: уточнить точный маршрут после появления ветки.
"""
import allure
import pytest

from ui.pages.activity_page import ActivityPage
from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 11: запись вебинара")
@pytest.mark.ui
@pytest.mark.mts_link
class TestRecording:
    @allure.title("Запись проигрывается прямо в «Результатах активности»")
    @pytest.mark.smoke
    def test_recording_plays_inline_in_activity_results(self, user_page, created_schedule_item, mts_link_endpoint):
        """Предусловие: запись вебинара получена и сохранена, слушателю доступна."""
        item = created_schedule_item(item_type="mts_link", url="")
        recording = mts_link_endpoint.get_recording_info(item["id"])
        assert recording.get("status") == "ready", recording

        activity_page = ActivityPage(user_page)
        assert activity_page.is_recording_player_visible() is True

    @allure.title("Досмотр записи до конца засчитывает посещение, если очно не засчитано")
    def test_watching_recording_to_end_credits_attendance_when_not_credited_onsite(
        self, user_page, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушатель не был на вебинаре (или процент ниже 75%), посещение не засчитано очно."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        activity_page = ActivityPage(user_page)
        activity_page.play_recording_to_end()

        stream_listeners_page.page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
        )
        stream_listeners_page.open_listeners_tab()
        assert stream_listeners_page.is_attendance_checkmark(listener["id"], item["id"]) is True

    @allure.title("Уже засчитанное очно посещение не меняется просмотром записи")
    def test_recording_playback_does_not_change_already_credited_attendance(
        self, user_page, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушателю посещение уже засчитано очно (>=75%)."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        stream_listeners_page.page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
        )
        stream_listeners_page.open_listeners_tab()
        before = stream_listeners_page.attendance_cell_text(listener["id"], item["id"])

        activity_page = ActivityPage(user_page)
        activity_page.play_recording_to_end()

        stream_listeners_page.page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
        )
        stream_listeners_page.open_listeners_tab()
        after = stream_listeners_page.attendance_cell_text(listener["id"], item["id"])
        assert after == before
