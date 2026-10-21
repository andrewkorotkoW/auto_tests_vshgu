"""Сценарий aos: анкеты обратной связи (АОС, type=feedback). АОС живёт не сама по себе,
а привязывается к элементу расписания потока, поэтому сценарий сначала создаёт
носитель — программа → поток → модуль, затем на каждую анкету свой элемент
расписания (очные элементы в одном модуле не могут пересекаться по времени — слоты
сдвигаются на 2 часа, как в activities) → АОС с одним вопросом, активированная в
потоке (POST …/feedback/{id}/change-active), чтобы слушателю её было видно.
"""
from datetime import datetime, timedelta

from api.endpoints.aos import AosEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.schedule_items import ScheduleItemsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.tests import TestsEndpoint
from api.helpers.data_generator import (
    generate_aos_payload,
    generate_module_payload,
    generate_program_payload,
    generate_question_payload,
    generate_schedule_item_payload,
    generate_stream_payload,
)
from utils.logger import logger

DESCRIPTION = "программа -> поток -> модуль -> N элементов расписания с анкетой обратной связи (АОС) на каждом, активированы"
COUNT_HELP = "анкет (по элементу расписания на каждую)"


def run(ctx) -> None:
    programs_ep = ProgramsEndpoint(ctx.api_client)
    streams_ep = StreamsEndpoint(ctx.api_client)
    modules_ep = ModulesEndpoint(ctx.api_client)
    schedule_ep = ScheduleItemsEndpoint(ctx.api_client)
    aos_ep = AosEndpoint(ctx.api_client)
    tests_ep = TestsEndpoint(ctx.api_client)

    logger.info("1. Программа -> поток -> модуль (носитель элементов расписания)...")
    program = programs_ep.create(generate_program_payload(name=ctx.name("Program")))
    ctx.manifest.record("program", program["id"], "programs.mass_delete([id])")
    stream = streams_ep.create(program["id"], generate_stream_payload(name=ctx.name("Stream")))
    ctx.manifest.record("stream", [program["id"], stream["id"]], "streams.delete(program_id, stream_id)")
    module = modules_ep.create(program["id"], stream["id"], generate_module_payload(name=ctx.name("Module")))
    ctx.manifest.record("module", [program["id"], stream["id"], module["id"]],
                         "modules.delete(program_id, stream_id, module_id)")

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        slot = datetime.now() + timedelta(hours=2 * i)
        logger.info(f"2. Элемент расписания {i + 1}/{ctx.count} ({slot:%d.%m %H:%M}) + АОС...")
        item = schedule_ep.create(program["id"], stream["id"], module["id"], generate_schedule_item_payload(
            name=ctx.name(f"Item{suffix}"),
            date_time_from=slot.strftime("%Y-%m-%dT%H:%M"),
            date_time_to=(slot + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        ))
        ctx.manifest.record("schedule_item", [program["id"], stream["id"], module["id"], item["id"]],
                             "schedule_items.delete(program_id, stream_id, module_id, item_id)")

        aos = aos_ep.create(generate_aos_payload(name=ctx.name(f"AOS{suffix}"), schedule_item_ids=[item["id"]]))
        aos_id = aos.get("content_id", aos.get("id"))
        ctx.manifest.record("aos", aos_id, "aos.mass_delete([id])")
        # Вопрос АОС хранится там же, где вопросы тестов/опросов (PUT /tests/questions/store);
        # группа обязательна — generate_question_payload её проставляет.
        tests_ep.create_question(aos_id, generate_question_payload(order=1, text="Оцените занятие"))
        activated = aos_ep.activate(program["id"], stream["id"], aos_id)
        logger.info(f"   АОС {aos_id} {'активирована' if activated else 'НЕ активирована'} в потоке {stream['id']}")

    logger.info("Готово.")
    logger.info(f"  Программа: {program['id']}, поток: {stream['id']}, модуль: {module['id']}")
