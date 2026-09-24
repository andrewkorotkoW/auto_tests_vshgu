"""Общие фикстуры для tests/api и tests/ui (видны в обоих поддеревьях).

Пока здесь только данные для «Статистика обучения → Курсы» — переиспользуются и
API-, и UI-тестами (tests/api/learning_statistics, tests/ui/learning_statistics), см.
docs/plans/statistics_courses_plan.md.
"""
import pytest


@pytest.fixture
def course_with_listeners(
    created_program,
    created_stream,
    created_module,
    created_tincan,
    created_user,
    assignments_endpoint,
    modules_endpoint,
    tincan_endpoint,
    dashboards_endpoint,
):
    """Фабрика: программа → поток → модуль → курс Tincan (с разделами, архив по
    умолчанию — test_data/course_tincan.zip, тот же курс, что эталонный id=4393 на
    develop) → N слушателей, назначенных на поток (по умолчанию 1). Ждёт появления
    строки статистики курса перед возвратом — статистика считается асинхронно."""

    def _create(user_count: int = 1, **course_kwargs):
        program = created_program()
        stream = created_stream(program_id=program["id"])
        module = created_module(program_id=program["id"], stream_id=stream["id"])

        cover = tincan_endpoint.upload_cover()
        archive = tincan_endpoint.upload_archive()
        sub = tincan_endpoint.upload_sub_file()
        course = created_tincan(
            archive_uuid=archive, cover_uuid=cover, sub_files_uuids=[sub], **course_kwargs
        )
        tincan_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [course["id"]])
        stream_content_id = modules_endpoint.find_stream_content_id(
            program["id"], stream["id"], module["id"], course["id"]
        )

        users = [created_user() for _ in range(user_count)]
        user_ids = [u["id"] for u in users]
        if user_ids:
            assignments_endpoint.assign(program["id"], stream["id"], user_ids)

        row = dashboards_endpoint.wait_for_course_row(course["name"], stream["id"])

        return {
            "program_id": program["id"],
            "program_name": program["name"],
            "stream_id": stream["id"],
            "stream_name": stream["name"],
            "module_id": module["id"],
            "course_id": course["id"],
            "course_name": course["name"],
            "stream_content_id": stream_content_id,
            "users": users,
            "row": row,
        }

    return _create


@pytest.fixture
def course_without_listeners(
    created_program, created_stream, created_module, created_tincan, tincan_endpoint, modules_endpoint,
):
    """Курс Tincan, назначенный в модуль, но без единого слушателя — для проверки
    состояния карты/таблицы «данных нет» (шаг 4 плана)."""
    program = created_program()
    stream = created_stream(program_id=program["id"])
    module = created_module(program_id=program["id"], stream_id=stream["id"])

    cover = tincan_endpoint.upload_cover()
    archive = tincan_endpoint.upload_archive()
    sub = tincan_endpoint.upload_sub_file()
    course = created_tincan(archive_uuid=archive, cover_uuid=cover, sub_files_uuids=[sub])
    tincan_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [course["id"]])

    return {
        "program_id": program["id"],
        "stream_id": stream["id"],
        "module_id": module["id"],
        "course_id": course["id"],
        "course_name": course["name"],
    }
