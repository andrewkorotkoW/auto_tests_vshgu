"""Часть 4 — синхронизация лекторов (docs/test_cases/mts_link/05_lecturers.md)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 4: синхронизация лекторов")
@pytest.mark.api
@pytest.mark.mts_link
class TestLecturers:
    @allure.title("Преподавателя назначили → добавлен ведущим на вебинар")
    @pytest.mark.smoke
    def test_assign_teacher_adds_as_lecturer(self, mts_link_endpoint, created_schedule_item, created_user):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        assert mts_link_endpoint.wait_for_part_status(item["id"], "creation") == "success"

        assert mts_link_endpoint.wait_for_part_status(item["id"], "lecturers") == "success"
        state = mts_link_endpoint.get_lecturer_sync_state(item["id"], teacher["id"])
        assert state is not None
        assert state.get("role") == "LECTURER"
        assert state.get("join_link")

    @allure.title("Преподавателя сняли → удалён с вебинара")
    def test_unassign_teacher_removes_lecturer(self, mts_link_endpoint, created_schedule_item, created_user):
        """Предусловие: преподаватель уже назначен и синхронизирован."""
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        assert mts_link_endpoint.wait_for_part_status(item["id"], "lecturers") == "success"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"teacher_ids": []},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.wait_for_part_status(item["id"], "lecturers") == "success"

        state = mts_link_endpoint.get_lecturer_sync_state(item["id"], teacher["id"])
        assert state is None or state.get("soft_deleted") is True

    @allure.title("Ошибка по одному лектору не блокирует остальных")
    def test_lecturer_error_for_one_does_not_block_others(self, mts_link_endpoint, created_schedule_item, created_user):
        """Предусловие: мок отвечает отказом по одному из назначенных преподавателей."""
        ok_teacher = created_user()
        broken_teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[ok_teacher["id"], broken_teacher["id"]])

        status = mts_link_endpoint.wait_for_part_status(item["id"], "lecturers")
        assert status == "error", status
        ok_state = mts_link_endpoint.get_lecturer_sync_state(item["id"], ok_teacher["id"])
        assert ok_state and ok_state.get("join_link")
        broken_state = mts_link_endpoint.get_lecturer_sync_state(item["id"], broken_teacher["id"])
        assert not (broken_state and broken_state.get("join_link"))

    @allure.title("Ошибка синхронизации лекторов не блокирует участников и файлы")
    def test_lecturer_sync_error_does_not_block_participants_and_files(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мок отвечает ошибкой только по операции добавления лектора."""
        broken_teacher = created_user()
        listener = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[broken_teacher["id"]])
        schedule_items_endpoint.register_user(item["id"], listener["id"])

        assert mts_link_endpoint.wait_for_part_status(item["id"], "participants") == "success"
        assert mts_link_endpoint.wait_for_part_status(item["id"], "lecturers") == "error"

    @allure.title("Повторная сверка добивает лекторов")
    def test_repeated_sync_completes_failed_lecturers(self, mts_link_endpoint, created_schedule_item, created_user):
        """Предусловие: лектор не назначен из-за прошлой ошибки, мок теперь отвечает успехом."""
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])

        assert mts_link_endpoint.wait_for_part_status(item["id"], "lecturers", timeout=90.0) == "success"
        state = mts_link_endpoint.get_lecturer_sync_state(item["id"], teacher["id"])
        assert state and state.get("join_link")
