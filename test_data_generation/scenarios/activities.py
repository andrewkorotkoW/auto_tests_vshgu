"""Сценарий activities: программа -> поток -> модуль (носитель активностей) -> по одной
активности каждого типа, каждая назначается в модуль через AssignmentsEndpoint.
assign_content_to_module (один и тот же mass-addition эндпоинт для всех типов контента).

LPD создаётся только при --env stage (см. tests/api/create_activity/lpd — маркер
env("stage")); на develop шаг помечается пропущенным и в логе, и в манифесте.
Достижение (achievement) создаётся только через UI (ui/pages/admin_knowledge_base_page.py) —
в api/endpoints/knowledge_base.py нет метода создания достижения, поэтому шаг тоже
только помечается, без выдумывания несуществующего эндпоинта.
"""
from api.endpoints.aos import AosEndpoint
from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.external_content import ExternalContentEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.homework_pass_fail import HomeworkPassFailEndpoint
from api.endpoints.homework_ten_point import HomeworkTenPointEndpoint
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.endpoints.lpd import LpdEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.polls import PollsEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.schedule_items import ScheduleItemsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.tests import TestsEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import (
    generate_aos_payload,
    generate_external_content_payload,
    generate_homework_pass_fail_payload,
    generate_homework_payload,
    generate_homework_ten_point_payload,
    generate_lpd_payload,
    generate_material_payload,
    generate_module_payload,
    generate_poll_payload,
    generate_program_payload,
    generate_question_payload,
    generate_schedule_item_payload,
    generate_scorm_payload,
    generate_stream_payload,
    generate_test_payload,
    generate_tincan_payload,
    get_next_lpd_id,
)
from utils.logger import logger

DESCRIPTION = ("программа -> поток -> модуль -> по одной активности каждого типа "
               "(tincan/scorm/внешний контент/ДЗ 5-10-зачёт/тест/опрос/АОС/LPD на stage/"
               "материал БЗ + достижение)")

LPD_STAGE_ONLY_REASON = "LPD доступен только на stage, пропущено"
ACHIEVEMENT_UI_ONLY_REASON = (
    "achievement — только через UI, API-путь отсутствует "
    "(в api/endpoints/knowledge_base.py есть create_material/toggle_visibility, "
    "но метода создания достижения нет; см. ui/pages/admin_knowledge_base_page.py)"
)


def run(ctx) -> None:
    programs_ep = ProgramsEndpoint(ctx.api_client)
    streams_ep = StreamsEndpoint(ctx.api_client)
    modules_ep = ModulesEndpoint(ctx.api_client)
    schedule_ep = ScheduleItemsEndpoint(ctx.api_client)
    assignments_ep = AssignmentsEndpoint(ctx.api_client)
    tincan_ep = TincanEndpoint(ctx.api_client)
    ext_content_ep = ExternalContentEndpoint(ctx.api_client)
    hw_ep = HomeworkEndpoint(ctx.api_client)
    hw10_ep = HomeworkTenPointEndpoint(ctx.api_client)
    hwpf_ep = HomeworkPassFailEndpoint(ctx.api_client)
    tests_ep = TestsEndpoint(ctx.api_client)
    polls_ep = PollsEndpoint(ctx.api_client)
    aos_ep = AosEndpoint(ctx.api_client)
    lpd_ep = LpdEndpoint(ctx.api_client)
    kb_ep = KnowledgeBaseEndpoint(ctx.api_client)

    logger.info("1. Программа -> поток -> модуль (носитель активностей)...")
    program = programs_ep.create(generate_program_payload(name=ctx.name("Program")))
    ctx.manifest.record("program", program["id"], "programs.mass_delete([id])")
    stream = streams_ep.create(program["id"], generate_stream_payload(name=ctx.name("Stream")))
    ctx.manifest.record("stream", [program["id"], stream["id"]], "streams.delete(program_id, stream_id)")
    module = modules_ep.create(program["id"], stream["id"], generate_module_payload(name=ctx.name("Module")))
    ctx.manifest.record("module", [program["id"], stream["id"], module["id"]],
                         "modules.delete(program_id, stream_id, module_id)")

    def assign(content_id, label: str) -> None:
        ok = assignments_ep.assign_content_to_module(program["id"], stream["id"], module["id"], [content_id])
        logger.info(f"   {label} {'назначен' if ok else 'НЕ назначен'} в модуль {module['id']}")

    for i in range(ctx.count):
        suffix = f"_{i}" if ctx.count > 1 else ""

        logger.info(f"2. Tincan-курс{suffix}...")
        archive_uuid = ctx.dry_or(
            "upload_archive(test_data/course_tincan.zip)",
            "00000000-0000-0000-0000-000000000001",
            lambda: tincan_ep.upload_archive("test_data/course_tincan.zip"),
        )
        tincan = tincan_ep.create(generate_tincan_payload(name=ctx.name(f"Tincan{suffix}"), archive_uuid=archive_uuid))
        ctx.manifest.record("tincan", tincan["id"], "tincan.mass_delete([id])")
        assign(tincan["id"], "Tincan-курс")

        logger.info(f"3. SCORM-курс{suffix}...")
        scorm_archive_uuid = ctx.dry_or(
            "upload_archive(test_data/test_lms_scorm_2004.zip)",
            "00000000-0000-0000-0000-000000000002",
            lambda: tincan_ep.upload_archive("test_data/test_lms_scorm_2004.zip"),
        )
        scorm = tincan_ep.create(generate_scorm_payload(name=ctx.name(f"Scorm{suffix}"), archive_uuid=scorm_archive_uuid))
        ctx.manifest.record("scorm", scorm["id"], "tincan.mass_delete([id])")
        assign(scorm["id"], "SCORM-курс")

        logger.info(f"4. Внешний контент{suffix}...")
        external = ext_content_ep.create(generate_external_content_payload(name=ctx.name(f"External{suffix}")))
        ctx.manifest.record("external_content", external["id"], "external_content.delete(content_id)")
        assign(external["id"], "Внешний контент")

        logger.info(f"5. Домашнее задание (5-балльное){suffix}...")
        hw5 = hw_ep.create(generate_homework_payload(name=ctx.name(f"HW5{suffix}"), teacher_ids=[], inspector_ids=[]))
        ctx.manifest.record("homework_five_point", hw5["id"], "homework.mass_delete([id])")
        assign(hw5["id"], "ДЗ (5-балльное)")

        logger.info(f"6. Домашнее задание (10-балльное){suffix}...")
        hw10 = hw10_ep.create(generate_homework_ten_point_payload(name=ctx.name(f"HW10{suffix}"), teacher_ids=[], inspector_ids=[]))
        ctx.manifest.record("homework_ten_point", hw10["id"], "homework_ten_point.mass_delete([id])")
        assign(hw10["id"], "ДЗ (10-балльное)")

        logger.info(f"7. Домашнее задание (зачёт/незачёт){suffix}...")
        hwpf = hwpf_ep.create(generate_homework_pass_fail_payload(name=ctx.name(f"HWPF{suffix}"), teacher_ids=[], inspector_ids=[]))
        ctx.manifest.record("homework_pass_fail", hwpf["id"], "homework_pass_fail.mass_delete([id])")
        assign(hwpf["id"], "ДЗ (зачёт/незачёт)")

        logger.info(f"8. Тест с вопросом (группа привязывается автоматически){suffix}...")
        test = tests_ep.create(generate_test_payload(name=ctx.name(f"Test{suffix}")))
        ctx.manifest.record("test", test["id"], "tests.mass_delete([id])")
        tests_ep.create_question(test["id"], generate_question_payload(order=1, text="Вопрос теста"))
        assign(test["id"], "Тест")

        logger.info(f"9. Опрос с вопросом{suffix}...")
        poll = polls_ep.create(generate_poll_payload(name=ctx.name(f"Poll{suffix}")))
        ctx.manifest.record("poll", poll["id"], "polls.mass_delete([id])")
        polls_ep.create_question(poll["id"], generate_question_payload(order=1, text="Вопрос опроса"))
        assign(poll["id"], "Опрос")

        logger.info(f"10. Элемент расписания + АОС{suffix} (АОС привязывается к schedule_item, "
                    "а не назначается в модуль mass-addition)...")
        item = schedule_ep.create(program["id"], stream["id"], module["id"],
                                   generate_schedule_item_payload(name=ctx.name(f"ItemForAos{suffix}")))
        ctx.manifest.record("schedule_item", [program["id"], stream["id"], module["id"], item["id"]],
                             "schedule_items.delete(program_id, stream_id, module_id, item_id)")
        aos = aos_ep.create(generate_aos_payload(name=ctx.name(f"AOS{suffix}"), schedule_item_ids=[item["id"]]))
        aos_id = aos.get("content_id", aos.get("id"))
        ctx.manifest.record("aos", aos_id, "aos.mass_delete([id])")

        logger.info(f"11. LPD{suffix}...")
        if ctx.env.name != "stage":
            logger.info(f"   {LPD_STAGE_ONLY_REASON} (окружение: {ctx.env.name})")
            ctx.manifest.skip("lpd", LPD_STAGE_ONLY_REASON)
        else:
            lpd = lpd_ep.create(generate_lpd_payload(lpd_id=get_next_lpd_id(), name=ctx.name(f"LPD{suffix}")))
            ctx.manifest.record("lpd", lpd["id"], "lpd.mass_delete([id])")
            assign(lpd["id"], "LPD")

        logger.info(f"12. Материал базы знаний, привязан к Tincan-курсу{suffix} "
                    "(по умолчанию создаётся скрытым — публикуем через toggle_visibility)...")
        material = kb_ep.create_material(generate_material_payload(name=ctx.name(f"KB{suffix}"), content_id=tincan["id"]))
        ctx.manifest.record("knowledge_base_material", material["id"], "knowledge_base.delete_materials([id])")
        kb_ep.toggle_visibility(material["id"], is_visible=True)

        logger.info(f"13. Достижение{suffix}...")
        ctx.manifest.skip("achievement", ACHIEVEMENT_UI_ONLY_REASON)

    logger.info("Готово.")
    logger.info(f"  Программа: {program['id']}, поток: {stream['id']}, модуль: {module['id']}")
