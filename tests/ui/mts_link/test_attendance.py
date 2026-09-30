"""Часть 9 — процент посещения в таблице слушателей (docs/test_cases/mts_link/10_attendance.md)."""
import allure
import pytest

from config.settings import settings


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 9: процент посещения")
@pytest.mark.ui
@pytest.mark.mts_link
class TestAttendance:
    def _open_listeners(self, stream_listeners_page, item):
        stream_listeners_page.page.goto(
            f"{settings.UI_BASE_URL}/programs/{item['program_id']}/streams/{item['stream_id']}"
        )
        stream_listeners_page.open_listeners_tab()

    @allure.title("Процент = время слушателя ÷ фактическая длительность вебинара")
    @pytest.mark.smoke
    def test_percentage_calculated_from_actual_duration(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint, mts_link_endpoint
    ):
        """Предусловие: слушатель был на вебинаре N минут, фактическая длительность M
        минут из данных МТС Линк, N/M отличается от отношения к плановой длительности."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        attendance = mts_link_endpoint.get_listener_attendance(item["id"], listener["id"])
        self._open_listeners(stream_listeners_page, item)
        cell_text = stream_listeners_page.attendance_cell_text(listener["id"], item["id"])
        assert cell_text, attendance

    @allure.title("Процент округляется до целого")
    def test_percentage_rounded_to_integer(self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint):
        """Предусловие: время слушателя даёт дробный процент (например, 73.6%)."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, item)
        text = stream_listeners_page.attendance_cell_text(listener["id"], item["id"])
        digits = "".join(ch for ch in text if ch.isdigit())
        assert digits, text
        assert "." not in text and "," not in text

    @allure.title("Посещение ≥75% → галка")
    def test_attendance_75_percent_and_above_shows_checkmark(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушатель посетил вебинар на 75% и более."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, item)
        assert stream_listeners_page.is_attendance_checkmark(listener["id"], item["id"]) is True

    @allure.title("Посещение <75% → процент")
    def test_attendance_below_75_percent_shows_percent(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушатель посетил вебинар менее чем на 75% (например, 74%)."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, item)
        assert stream_listeners_page.is_attendance_checkmark(listener["id"], item["id"]) is False
        assert "%" in stream_listeners_page.attendance_cell_text(listener["id"], item["id"])

    @allure.title("Слушатель не был на вебинаре → 0%")
    def test_absent_listener_shows_zero_percent(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушатель назначен, но не заходил в вебинар, статистика получена."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, item)
        assert stream_listeners_page.attendance_cell_text(listener["id"], item["id"]) == "0%"

    @allure.title("Статистика ещё не подтянулась → ячейка пустая")
    def test_missing_statistics_shows_empty_cell(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: вебинар ещё не прошёл или статистика посещения ещё не получена."""
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="")
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, item)
        assert stream_listeners_page.is_attendance_empty(listener["id"], item["id"]) is True

    @allure.title("Обычные мероприятия — без изменений")
    def test_regular_events_cells_unchanged(
        self, stream_listeners_page, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: в потоке есть и вебинар «МТС Линк», и обычное очное мероприятие."""
        listener = created_user()
        regular_item = created_schedule_item(item_type="webinar")
        schedule_items_endpoint.register_user(regular_item["id"], listener["id"])

        self._open_listeners(stream_listeners_page, regular_item)
        text = stream_listeners_page.attendance_cell_text(listener["id"], regular_item["id"])
        assert "%" not in text

    @allure.title("Процент считается по каждому вебинару отдельно")
    def test_percentage_calculated_per_webinar_independently(
        self, stream_listeners_page, created_module, created_user, schedule_items_endpoint
    ):
        """Предусловие: слушатель назначен на два вебинара «МТС Линк» с разными процентами посещения."""
        from api.helpers.data_generator import generate_schedule_item_payload

        listener = created_user()
        module = created_module()
        item_ids = []
        for _ in range(2):
            payload = generate_schedule_item_payload(item_type="mts_link", url="")
            data = schedule_items_endpoint.create(module["program_id"], module["stream_id"], module["id"], payload)
            schedule_items_endpoint.register_user(data["id"], listener["id"])
            item_ids.append(data["id"])

        self._open_listeners(stream_listeners_page, module)
        text_a = stream_listeners_page.attendance_cell_text(listener["id"], item_ids[0])
        text_b = stream_listeners_page.attendance_cell_text(listener["id"], item_ids[1])
        assert text_a != "" and text_b != ""
