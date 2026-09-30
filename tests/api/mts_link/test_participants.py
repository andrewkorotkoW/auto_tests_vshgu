"""Часть 3 — синхронизация участников (docs/test_cases/mts_link/04_participants.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 3: синхронизация участников")
@pytest.mark.api
@pytest.mark.mts_link
class TestParticipants:
    @allure.title("Первичная регистрация всех слушателей потока")
    @pytest.mark.smoke
    def test_initial_registration_of_all_listeners(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» только что создано, поток с несколькими слушателями."""
        item = created_schedule_item(item_type="mts_link", url="")
        listeners = [created_user() for _ in range(2)]
        for listener in listeners:
            schedule_items_endpoint.register_user(item["id"], listener["id"])

        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"
        for listener in listeners:
            state = mts_link_endpoint.get_participant_sync_state(item["id"], listener["id"])
            assert state is not None, listener["id"]
            assert state.get("personal_link")

    @allure.title("Добавили слушателя → зарегистрирован с персональной ссылкой")
    def test_add_listener_registers_with_personal_link(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="")
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        listener = created_user()
        schedule_items_endpoint.register_user(item["id"], listener["id"])
        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"

        state = mts_link_endpoint.get_participant_sync_state(item["id"], listener["id"])
        assert state["personal_link"]

    @allure.title("Убрали слушателя до вебинара → удалён + софт-делит")
    def test_remove_listener_before_webinar_deletes_and_soft_deletes(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: вебинар ещё не начался, слушатель зарегистрирован."""
        item = created_schedule_item(item_type="mts_link", url="")
        listener = created_user()
        schedule_items_endpoint.register_user(item["id"], listener["id"])
        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"

        schedule_items_endpoint.register_user(item["id"], listener["id"], is_registered=False)
        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"

        state = mts_link_endpoint.get_participant_sync_state(item["id"], listener["id"])
        assert state is None or state.get("soft_deleted") is True

    @allure.title("Убрали слушателя после вебинара → регистрация не тронута")
    def test_remove_listener_after_webinar_keeps_registration(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: вебинар уже прошёл, слушатель был зарегистрирован."""
        item = created_schedule_item(
            item_type="mts_link", url="",
            date_time_from="2020-01-01T10:00", date_time_to="2020-01-01T11:00",
        )
        listener = created_user()
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        before = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="delete")
        schedule_items_endpoint.register_user(item["id"], listener["id"], is_registered=False)
        after = mts_link_endpoint.get_request_log_entries(schedule_item_id=item["id"], operation="delete")
        assert len(after) == len(before)

        state = mts_link_endpoint.get_participant_sync_state(item["id"], listener["id"])
        assert state is not None and state.get("soft_deleted") is True

    @allure.title("Ошибка регистрации одного слушателя не блокирует остальных")
    def test_registration_error_for_one_does_not_block_others(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мок отвечает отказом по конкретному слушателю (объекту), остальные — успех."""
        item = created_schedule_item(item_type="mts_link", url="")
        ok_listener = created_user()
        broken_listener = created_user()
        for listener in (ok_listener, broken_listener):
            schedule_items_endpoint.register_user(item["id"], listener["id"])

        status = mts_link_endpoint.wait_for_part_status(item["id"], "participants")
        assert status == "error", status

        ok_state = mts_link_endpoint.get_participant_sync_state(item["id"], ok_listener["id"])
        assert ok_state and ok_state.get("personal_link")
        broken_state = mts_link_endpoint.get_participant_sync_state(item["id"], broken_listener["id"])
        assert not (broken_state and broken_state.get("personal_link"))

    @allure.title("Повторная сверка добивает незарегистрированных")
    def test_repeated_sync_completes_failed_registrations(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: часть слушателей не зарегистрирована из-за прошлой ошибки,
        мок теперь отвечает успехом."""
        item = created_schedule_item(item_type="mts_link", url="")
        listener = created_user()
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants", timeout=90.0) == "success"
        state = mts_link_endpoint.get_participant_sync_state(item["id"], listener["id"])
        assert state and state.get("personal_link")
