"""Часть 4 — синхронизация лекторов (docs/test_cases/mts_link/05_lecturers.md).

02.11.2026: сведено с реальным контрактом (живая разведка на mts-link-release-main)
— нет эндпоинта с детализацией по отдельному лектору (роль/личная ссылка), только
агрегированный lecturers_sync_status; проверки ниже смотрят на него + на то, что
преподаватель присутствует/отсутствует в attributes.teachers самого элемента
расписания (это подтверждённое поле, не придуманное).

3 теста удалены: «ошибка по одному лектору не блокирует остальных» и «ошибка
синхронизации лекторов не блокирует участников/файлы» требуют РАЗНОГО исхода для
разных лекторов одновременно — без детализации по отдельному лектору это
непроверяемо (виден только общий lecturers_sync_status на всех разом). «Повторная
сверка добивает лекторов» требует заранее созданного состояния «ошибка из-за
прошлого сбоя», которое нечем спровоцировать на реальном проде (нет мока)."""
import allure
import pytest


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 4: синхронизация лекторов")
@pytest.mark.api
@pytest.mark.mts_link
class TestLecturers:
    @allure.title("Преподавателя назначили → добавлен ведущим на вебинар")
    @pytest.mark.smoke
    def test_assign_teacher_adds_as_lecturer(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        assert mts_link_endpoint.wait_for_part_status(item, "creation") == "synced"

        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"
        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        teacher_ids = {t["id"] for t in fetched["attributes"].get("teachers", [])}
        assert teacher["id"] in teacher_ids

    @allure.title("Преподавателя сняли → удалён с вебинара")
    def test_unassign_teacher_removes_lecturer(
        self, mts_link_endpoint, created_schedule_item, created_user, schedule_items_endpoint
    ):
        """Предусловие: преподаватель уже назначен и синхронизирован."""
        teacher = created_user()
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[teacher["id"]])
        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"teacher_ids": []},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        teacher_ids = {t["id"] for t in fetched["attributes"].get("teachers", [])}
        assert teacher["id"] not in teacher_ids
