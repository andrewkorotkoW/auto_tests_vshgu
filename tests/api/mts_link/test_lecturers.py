"""Часть 4 — синхронизация лекторов (docs/test_cases/mts_link/05_lecturers.md).

02.11.2026: сведено с реальным контрактом (живая разведка на mts-link-release-main)
— нет эндпоинта с детализацией по отдельному лектору (роль/личная ссылка), только
агрегированный lecturers_sync_status; проверки ниже смотрят на него + на то, что
преподаватель присутствует/отсутствует в attributes.teachers самого элемента
расписания.

12.11.2026 (live run #131, test_hub): test_assign_teacher_adds_as_lecturer падал —
attributes.teachers оставался [] даже при lecturers_sync_status=success. Причина (видна
в debug-SQL бэкенда, warning_queries ответа): запрос, которым считается teachers,
требует EXISTS по таблице experts_users (deleted_at IS NULL) — показывает только
пользователей, ОТДЕЛЬНО зарегистрированных как «эксперты», не любого created_user().
Это не баг и не придуманное поле, просто созданный тестом обычный пользователь в
эксперты не попадает. Поэтому здесь, как и в остальном пакете mts_link, используем
штатного безопасного лектора — MTS_LINK_SAFE_TEACHER_ID (Вера, уже эксперт) — вместо
created_user(). test_unassign_teacher_removes_lecturer до этой правки проходил
«случайно»: assert teacher["id"] not in teacher_ids был вакуумным (множество и так
всегда было пустым) — теперь он содержательный (сначала проверяем, что Вера реально
попала в teachers, потом что её там не стало).

3 теста удалены: «ошибка по одному лектору не блокирует остальных» и «ошибка
синхронизации лекторов не блокирует участников/файлы» требуют РАЗНОГО исхода для
разных лекторов одновременно — без детализации по отдельному лектору это
непроверяемо (виден только общий lecturers_sync_status на всех разом). «Повторная
сверка добивает лекторов» требует заранее созданного состояния «ошибка из-за
прошлого сбоя», которое нечем спровоцировать на реальном проде (нет мока)."""
import allure
import pytest

from api.helpers.data_generator import MTS_LINK_SAFE_TEACHER_ID


@allure.feature("Интеграция МТС Линк")
@allure.story("Часть 4: синхронизация лекторов")
@pytest.mark.api
@pytest.mark.mts_link
class TestLecturers:
    @allure.title("Преподавателя назначили → добавлен ведущим на вебинар")
    @pytest.mark.smoke
    def test_assign_teacher_adds_as_lecturer(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: мероприятие «МТС Линк» со статусом «Успешно»."""
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[MTS_LINK_SAFE_TEACHER_ID])
        assert mts_link_endpoint.wait_for_part_status(item, "creation") == "synced"

        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"
        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        teacher_ids = {t["id"] for t in fetched["attributes"].get("teachers", [])}
        assert MTS_LINK_SAFE_TEACHER_ID in teacher_ids

    @allure.title("Преподавателя сняли → удалён с вебинара")
    def test_unassign_teacher_removes_lecturer(self, mts_link_endpoint, created_schedule_item, schedule_items_endpoint):
        """Предусловие: преподаватель уже назначен и синхронизирован."""
        item = created_schedule_item(item_type="mts_link", url="", teacher_ids=[MTS_LINK_SAFE_TEACHER_ID])
        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"
        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        teacher_ids_before = {t["id"] for t in fetched["attributes"].get("teachers", [])}
        assert MTS_LINK_SAFE_TEACHER_ID in teacher_ids_before, "Предусловие не выполнено: лектор не был назначен"

        resp = mts_link_endpoint.update_event(
            item["program_id"], item["stream_id"], item["module_id"], item["id"],
            attributes={"teacher_ids": []},
        )
        assert resp.status_code == 200, resp.text
        assert mts_link_endpoint.wait_for_part_status(item, "lecturers") == "success"

        fetched = schedule_items_endpoint.get(item["program_id"], item["stream_id"], item["module_id"], item["id"])
        teacher_ids = {t["id"] for t in fetched["attributes"].get("teachers", [])}
        assert MTS_LINK_SAFE_TEACHER_ID not in teacher_ids
