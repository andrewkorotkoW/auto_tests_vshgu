"""Сценарий scorm: N курсов SCORM 2004 (архив test_data/test_lms_scorm_2004.zip
загружается на каждый курс через тот же /upload/course_archive, что и Tincan; сам курс —
POST /content с content_type SCORM, см. generate_scorm_payload), без программы/потока.
Курсы Tincan — сценарий courses.
"""
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import generate_scorm_payload
from utils.logger import logger

DESCRIPTION = "N курсов SCORM 2004 (архив test_lms_scorm_2004.zip), без программы"
COUNT_HELP = "курсов SCORM"


def run(ctx) -> None:
    tincan_ep = TincanEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        logger.info(f"SCORM-курс {i + 1}/{ctx.count} (архив test_data/test_lms_scorm_2004.zip)...")
        archive_uuid = ctx.dry_or(
            "upload_archive(test_data/test_lms_scorm_2004.zip)",
            "00000000-0000-0000-0000-000000000002",
            lambda: tincan_ep.upload_archive("test_data/test_lms_scorm_2004.zip"),
        )
        scorm = tincan_ep.create(generate_scorm_payload(name=ctx.name(f"Scorm{suffix}"), archive_uuid=archive_uuid))
        ctx.manifest.record("scorm", scorm["id"], "tincan.mass_delete([id])")

    logger.info("Готово.")
