"""Сценарий learner_progress: программа -> поток -> модуль -> домашнее задание ->
N слушателей, назначенных на программу (AssignmentsEndpoint.assign). Дальше по заданию
нужно отправить ответ слушателя на ДЗ через API — такого метода нет ни в
api/endpoints/homework.py, ни в homework_ten_point.py/homework_pass_fail.py (там есть
только create/delete/mass_delete и examine()/get_status() со стороны преподавателя),
поэтому шаг помечается как доступный только через UI, без выдумывания эндпоинта.
"""
from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import (
    generate_homework_payload,
    generate_module_payload,
    generate_program_payload,
    generate_stream_payload,
    generate_user_payload,
)
from utils.logger import logger

from lib import DEFAULT_PASSWORD

DESCRIPTION = "слушатель -> назначение на программу с ДЗ в модуле -> отправка ответа (только через UI — нет API)"

HOMEWORK_ANSWER_UI_ONLY_REASON = (
    "отправка ответа слушателем на ДЗ — только через UI, API-путь отсутствует "
    "(в api/endpoints/homework.py/homework_ten_point.py/homework_pass_fail.py есть только "
    "create/delete/mass_delete и examine()/get_status() со стороны преподавателя, "
    "метода отправки ответа слушателем нет)"
)


def run(ctx) -> None:
    programs_ep = ProgramsEndpoint(ctx.api_client)
    streams_ep = StreamsEndpoint(ctx.api_client)
    modules_ep = ModulesEndpoint(ctx.api_client)
    assignments_ep = AssignmentsEndpoint(ctx.api_client)
    hw_ep = HomeworkEndpoint(ctx.api_client)
    users_ep = UsersEndpoint(ctx.api_client)

    logger.info("1. Программа -> поток -> модуль -> домашнее задание...")
    program = programs_ep.create(generate_program_payload(name=ctx.name("Program")))
    ctx.manifest.record("program", program["id"], "programs.mass_delete([id])")
    stream = streams_ep.create(program["id"], generate_stream_payload(name=ctx.name("Stream")))
    ctx.manifest.record("stream", [program["id"], stream["id"]], "streams.delete(program_id, stream_id)")
    module = modules_ep.create(program["id"], stream["id"], generate_module_payload(name=ctx.name("Module")))
    ctx.manifest.record("module", [program["id"], stream["id"], module["id"]],
                         "modules.delete(program_id, stream_id, module_id)")
    homework = hw_ep.create(generate_homework_payload(name=ctx.name("HW"), teacher_ids=[], inspector_ids=[]))
    ctx.manifest.record("homework_five_point", homework["id"], "homework.mass_delete([id])")
    ok = assignments_ep.assign_content_to_module(program["id"], stream["id"], module["id"], [homework["id"]])
    logger.info(f"   ДЗ {'назначено' if ok else 'НЕ назначено'} в модуль {module['id']}")

    logger.info(f"2. {ctx.count} слушателей -> назначение на программу...")
    listener_ids = []
    for i in range(ctx.count):
        listener = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
        ctx.manifest.record("user", listener["id"], "users.delete(user_id)")
        listener_ids.append(listener["id"])
        logger.info(f"   слушатель {i + 1}/{ctx.count}: ID={listener['id']}, email={listener['attributes']['email']}")
    assignments_ep.assign(program["id"], stream["id"], listener_ids)
    ctx.manifest.record("stream_assignment", [program["id"], stream["id"], listener_ids],
                         "нет DELETE-метода (AssignmentsEndpoint) — снять назначение вручную через админку")

    logger.info(f"3. {HOMEWORK_ANSWER_UI_ONLY_REASON}")
    ctx.manifest.skip("homework_answer_submit", HOMEWORK_ANSWER_UI_ONLY_REASON)

    logger.info("Готово.")
    logger.info(f"  Программа: {program['id']}, поток: {stream['id']}, ДЗ: {homework['id']}, слушатели: {listener_ids}")
