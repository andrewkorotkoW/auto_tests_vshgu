"""Сценарий courses: N курсов Tincan (архив test_data/course_tincan.zip загружается на
каждый курс) и на каждый — материал базы знаний типа «курс» (KnowledgeBaseEndpoint.
create_course_material, сразу видимый), без программы/потока. Это тот же путь, что у
фикстуры created_course в conftest.py, только без привязки к pytest.
"""
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import generate_tincan_payload
from utils.logger import logger

DESCRIPTION = "N курсов Tincan + материал БЗ «курс» на каждый, без программы"
COUNT_HELP = "курсов (и материалов БЗ к ним)"


def run(ctx) -> None:
    tincan_ep = TincanEndpoint(ctx.api_client)
    kb_ep = KnowledgeBaseEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""

        logger.info(f"Tincan-курс {i + 1}/{ctx.count} (архив test_data/course_tincan.zip)...")
        archive_uuid = ctx.dry_or(
            "upload_archive(test_data/course_tincan.zip)",
            "00000000-0000-0000-0000-000000000001",
            lambda: tincan_ep.upload_archive("test_data/course_tincan.zip"),
        )
        tincan = tincan_ep.create(generate_tincan_payload(name=ctx.name(f"Course{suffix}"), archive_uuid=archive_uuid))
        ctx.manifest.record("tincan", tincan["id"], "tincan.mass_delete([id])")

        logger.info(f"Материал БЗ «курс» {i + 1}/{ctx.count} поверх Tincan {tincan['id']}...")
        material = kb_ep.create_course_material(name=ctx.name(f"KBCourse{suffix}"), content_id=tincan["id"])
        ctx.manifest.record("knowledge_base_material", material["id"], "knowledge_base.delete_materials([id])")

    logger.info("Готово.")
