"""Фикстуры для тестов группового ПЗ (поток + модуль + ПЗ, добавленное в модуль).

Логика переносит tests/ui/cleanup/test_99_cleanup_practical_tasks_chain.py коллеги
(origin/feature/dashboard-autotests, отдельная история, ветка не сливалась) — там
удаление потока/программы/ПЗ/пользователей было отдельным тестом-очисткой, запускаемым
последним (test_99_*). В нашей архитектуре отдельного файла-очистки быть не должно:
поток/программа и пользователи уже удаляются через yield-teardown фикстур created_stream/
created_module (см. корневой conftest.py) и created_user — не хватало только ПЗ
(created_homework намеренно "НЕ удаляет после теста", см. её докстринг в корневом
conftest.py: не все сценарии, использующие ПЗ, хотят удалять его сразу после теста).
group_practical_task закрывает именно этот пробел для группового сценария.
"""
import pytest

from utils.logger import logger


@pytest.fixture
def group_practical_task(created_stream, created_module, created_homework, assignments_endpoint, homework_endpoint):
    """Создаёт поток → модуль → ПЗ и добавляет ПЗ в модуль. Удаляет ПЗ после теста
    (поток/программу удаляет created_stream, пользователей — created_user)."""
    homework_ids = []

    def _create(*, cover_uuid, archive_uuid, sub_files_uuids, teacher_ids, inspector_ids, **stream_kwargs):
        stream = created_stream(**stream_kwargs)
        module = created_module(program_id=stream["program_id"], stream_id=stream["id"])
        homework = created_homework(
            cover_uuid=cover_uuid,
            archive_uuid=archive_uuid,
            sub_files_uuids=sub_files_uuids,
            teacher_ids=teacher_ids,
            inspector_ids=inspector_ids,
        )
        homework_ids.append(homework["id"])

        assigned_ok = assignments_endpoint.assign_content_to_module(
            stream["program_id"], stream["id"], module["id"], [homework["id"]]
        )
        assert assigned_ok, "Не удалось добавить ПЗ в модуль"

        return stream, module, homework

    yield _create

    for homework_id in homework_ids:
        try:
            homework_endpoint.mass_delete([homework_id])
        except Exception as e:
            logger.warning(f"Failed to delete group homework {homework_id}: {e}")
