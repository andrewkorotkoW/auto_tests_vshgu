"""Сценарий certificates: шаблон сертификата для потока программы (type=program_stream)
и для активности (type=activity), оба назначаются через CertificatesEndpoint.assign_template
(один и тот же метод годится для обоих типов — см.
tests/api/certificates/assign/program/test_assign_template.py и
tests/api/certificates/assign/activity/test_assign_certificate_to_activity_and_user.py).

/certificates/template/assign ждёт content_id потока, а не id программы/потока
(см. коммит ac9cf39: 422 content_ids.0 иначе).
"""
from api.endpoints.certificates import CertificatesEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import (
    generate_certificate_template_payload,
    generate_homework_payload,
    generate_program_payload,
    generate_stream_payload,
)
from utils.logger import logger

DESCRIPTION = "шаблон сертификата для потока программы (program_stream) и для активности (activity) + назначение"


def run(ctx) -> None:
    programs_ep = ProgramsEndpoint(ctx.api_client)
    streams_ep = StreamsEndpoint(ctx.api_client)
    hw_ep = HomeworkEndpoint(ctx.api_client)
    tincan_ep = TincanEndpoint(ctx.api_client)
    certificates_ep = CertificatesEndpoint(ctx.api_client)

    logger.info("1. Программа -> поток (носитель шаблона program_stream)...")
    program = programs_ep.create(generate_program_payload(name=ctx.name("Program")))
    ctx.manifest.record("program", program["id"], "programs.mass_delete([id])")
    stream = streams_ep.create(program["id"], generate_stream_payload(name=ctx.name("Stream")))
    ctx.manifest.record("stream", [program["id"], stream["id"]], "streams.delete(program_id, stream_id)")

    logger.info("2. Домашнее задание (носитель шаблона activity)...")
    homework = hw_ep.create(generate_homework_payload(name=ctx.name("HW"), teacher_ids=[], inspector_ids=[]))
    ctx.manifest.record("homework_five_point", homework["id"], "homework.mass_delete([id])")

    logger.info("3. Файл шаблона сертификата (PDF)...")
    file_id = ctx.dry_or(
        "upload_certificate_file(test_data/certificat.pdf)",
        "00000000-0000-0000-0000-000000000000",
        tincan_ep.upload_certificate_file,
    )

    logger.info("4. Шаблон program_stream + назначение на поток...")
    content_id = stream["attributes"]["content_id"]
    template_stream = certificates_ep.create_template(generate_certificate_template_payload(
        file_id=file_id, template_type="program_stream", name=ctx.name("CertTemplateStream"),
    ))
    ctx.manifest.record("certificate_template", template_stream["id"], "certificates.delete_templates([id])")
    certificates_ep.assign_template(template_id=template_stream["id"], content_ids=[content_id])
    ctx.manifest.record("certificate_assignment", [template_stream["id"], content_id],
                         "нет DELETE-метода — снять шаблон с потока вручную через админку")

    logger.info("5. Шаблон activity + назначение на ДЗ...")
    template_activity = certificates_ep.create_template(generate_certificate_template_payload(
        file_id=file_id, template_type="activity", name=ctx.name("CertTemplateActivity"),
    ))
    ctx.manifest.record("certificate_template", template_activity["id"], "certificates.delete_templates([id])")
    certificates_ep.assign_template(template_id=template_activity["id"], content_ids=[homework["id"]])
    ctx.manifest.record("certificate_assignment", [template_activity["id"], homework["id"]],
                         "нет DELETE-метода — снять шаблон с активности вручную через админку")

    logger.info("Готово.")
    logger.info(f"  Программа: {program['id']}, поток: {stream['id']} (content_id={content_id}), ДЗ: {homework['id']}")
    logger.info(f"  Шаблон (поток): {template_stream['id']}, шаблон (активность): {template_activity['id']}")
