"""Сценарий program_full: программа -> поток (даты, менеджер) -> модуль -> элемент
расписания -> назначение N слушателей -> сертификатный шаблон программы, назначенный
на поток. Все шаги через существующие api/endpoints/* и генераторы data_generator.py.
"""
from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.certificates import CertificatesEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.schedule_items import ScheduleItemsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import (
    generate_certificate_template_payload,
    generate_module_payload,
    generate_program_payload,
    generate_schedule_item_payload,
    generate_stream_payload,
    generate_user_payload,
)
from utils.logger import logger

from lib import DEFAULT_PASSWORD

DESCRIPTION = "программа -> поток -> модуль -> элемент расписания -> N слушателей -> сертификатный шаблон программы"


def _create_role_user(ctx, users_ep, role_title: str, role_id: int) -> dict:
    user = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
    ctx.manifest.record("user", user["id"], "users.delete(user_id)")
    users_ep.assign_roles(user["id"], [role_id])
    logger.info(f"Пользователь [{role_title}] создан: ID={user['id']}, email={user['attributes']['email']}")
    return user


def run(ctx) -> None:
    users_ep = UsersEndpoint(ctx.api_client)
    programs_ep = ProgramsEndpoint(ctx.api_client)
    streams_ep = StreamsEndpoint(ctx.api_client)
    modules_ep = ModulesEndpoint(ctx.api_client)
    schedule_ep = ScheduleItemsEndpoint(ctx.api_client)
    assignments_ep = AssignmentsEndpoint(ctx.api_client)
    certificates_ep = CertificatesEndpoint(ctx.api_client)
    tincan_ep = TincanEndpoint(ctx.api_client)

    logger.info("1. Менеджер и преподаватель потока...")
    manager = _create_role_user(ctx, users_ep, "Менеджер", 3)
    teacher = _create_role_user(ctx, users_ep, "Преподаватель", 4)

    logger.info("2. Программа...")
    tenant_organization_id = str(ctx.tenant) if ctx.tenant else ""
    program = programs_ep.create(generate_program_payload(
        name=ctx.name("Program"), tenant_organization_id=tenant_organization_id,
    ))
    # DELETE /programs/{id} не поддержан (405) — удаляется только через mass_delete([id]).
    ctx.manifest.record("program", program["id"], "programs.mass_delete([id])")

    logger.info("3. Поток (даты по умолчанию + менеджер)...")
    stream_payload = generate_stream_payload(name=ctx.name("Stream"))
    stream_payload["data"]["attributes"]["managers_ids"] = [{"id": manager["id"], "is_visible": True}]
    stream = streams_ep.create(program["id"], stream_payload)
    ctx.manifest.record("stream", [program["id"], stream["id"]], "streams.delete(program_id, stream_id)")

    logger.info("4. Модуль...")
    module = modules_ep.create(program["id"], stream["id"], generate_module_payload(name=ctx.name("Module")))
    ctx.manifest.record("module", [program["id"], stream["id"], module["id"]],
                         "modules.delete(program_id, stream_id, module_id)")

    logger.info("5. Элемент расписания...")
    item = schedule_ep.create(program["id"], stream["id"], module["id"], generate_schedule_item_payload(
        name=ctx.name("Item"), teacher_ids=[teacher["id"]],
    ))
    ctx.manifest.record("schedule_item", [program["id"], stream["id"], module["id"], item["id"]],
                         "schedule_items.delete(program_id, stream_id, module_id, item_id)")

    logger.info(f"6. {ctx.count} слушателей + назначение в поток...")
    listener_ids = []
    for i in range(ctx.count):
        listener = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
        ctx.manifest.record("user", listener["id"], "users.delete(user_id)")
        listener_ids.append(listener["id"])
        logger.info(f"   слушатель {i + 1}/{ctx.count}: ID={listener['id']}, email={listener['attributes']['email']}")
    assignments_ep.assign(program["id"], stream["id"], listener_ids)
    ctx.manifest.record("stream_assignment", [program["id"], stream["id"], listener_ids],
                         "нет DELETE-метода (AssignmentsEndpoint) — снять назначение вручную через админку")

    logger.info("7. Сертификатный шаблон программы...")
    file_id = ctx.dry_or(
        "upload_certificate_file(test_data/certificat.pdf)",
        "00000000-0000-0000-0000-000000000000",
        tincan_ep.upload_certificate_file,
    )
    template = certificates_ep.create_template(generate_certificate_template_payload(
        file_id=file_id, template_type="program_stream", name=ctx.name("CertTemplate"),
    ))
    ctx.manifest.record("certificate_template", template["id"], "certificates.delete_templates([id])")

    # /certificates/template/assign ждёт content_id потока, а не id потока/программы
    # (см. коммит ac9cf39: 422 content_ids.0 иначе).
    content_id = stream["attributes"]["content_id"]
    certificates_ep.assign_template(template_id=template["id"], content_ids=[content_id])
    ctx.manifest.record("certificate_assignment", [template["id"], content_id],
                         "нет DELETE-метода — снять шаблон с программы вручную через админку")

    logger.info("Готово.")
    logger.info(f"  Программа: {program['id']}, поток: {stream['id']}, модуль: {module['id']}, "
                f"элемент расписания: {item['id']}")
    logger.info(f"  Менеджер: {manager['id']}, преподаватель: {teacher['id']}, слушатели: {listener_ids}")
    logger.info(f"  Шаблон сертификата: {template['id']} -> content_id={content_id}")
