"""Сценарий individual_track: N слушателей и по одной активности каждого типа, который
можно назначить на индивидуальный трек (POST /users/content/distant/assign-activities,
AssignmentsEndpoint.assign_to_individual): курс Tincan, курс SCORM, практические задания
трёх типов оценки, тест с вопросами, опрос с вопросом, LPD (только на stage). Игровую
сессию на инд. трек назначить нельзя (в продукте такой возможности нет), поэтому её в
сценарии нет. Внешний контент назначается, но после назначения на
инд. трек DELETE /content/{id} на develop отвечает 500 «Attempt to read property
"external_type" on null» (ContentObserver, 21.10.2026; через минуту удаляется штатно) —
чтобы --cleanup не оставлял хвостов, его в этом сценарии нет (есть в activities). Все активности
назначаются каждому слушателю — у него в «Индивидуальном обучении» появляется полный набор.

Слушатели подготовлены к UI (согласие на ПД, онбординг закрыт), пароль DEFAULT_PASSWORD.
Назначение записано в манифест отдельной сущностью individual_assignment сразу после
слушателей: при --cleanup сначала удаляются активности (ещё назначенными — это допустимо),
затем снимается назначение, затем удаляются пользователи (почему не наоборот — см.
комментарий у вставки записи ниже).
"""
from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.homework_pass_fail import HomeworkPassFailEndpoint
from api.endpoints.homework_ten_point import HomeworkTenPointEndpoint
from api.endpoints.lpd import LpdEndpoint
from api.endpoints.polls import PollsEndpoint
from api.endpoints.tests import TestsEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.users import UsersEndpoint
from api.helpers.data_generator import (
    generate_homework_pass_fail_payload,
    generate_homework_payload,
    generate_homework_ten_point_payload,
    generate_lpd_payload,
    generate_poll_payload,
    generate_question_payload,
    generate_scorm_payload,
    generate_test_payload,
    generate_tincan_payload,
    generate_user_payload,
    get_next_lpd_id,
)
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from utils.logger import logger

from lib import DEFAULT_PASSWORD
from scenarios.activities import LPD_STAGE_ONLY_REASON

DESCRIPTION = ("N слушателей + по одной активности каждого назначаемого типа (Tincan/SCORM/"
               "ДЗ 5-10-зачёт/тест/опрос/LPD на stage), все назначены на инд. трек каждому; "
               "без игровой сессии (на инд. трек не назначается) и внешнего контента")
COUNT_HELP = "слушателей (активности общие, назначены каждому)"


def run(ctx) -> None:
    users_ep = UsersEndpoint(ctx.api_client)
    assignments_ep = AssignmentsEndpoint(ctx.api_client)
    tincan_ep = TincanEndpoint(ctx.api_client)
    hw_ep = HomeworkEndpoint(ctx.api_client)
    hw10_ep = HomeworkTenPointEndpoint(ctx.api_client)
    hwpf_ep = HomeworkPassFailEndpoint(ctx.api_client)
    tests_ep = TestsEndpoint(ctx.api_client)
    polls_ep = PollsEndpoint(ctx.api_client)
    lpd_ep = LpdEndpoint(ctx.api_client)

    logger.info(f"1. {ctx.count} слушателей (подготовлены к UI)...")
    listeners = []
    for i in range(ctx.count):
        user = users_ep.create(generate_user_payload(password=DEFAULT_PASSWORD))
        ctx.manifest.record("user", user["id"], "users.delete(user_id)")
        email = user["attributes"]["email"]
        ctx.dry_or(
            f"prepare_user_for_tests_via_api(login={email})",
            None,
            lambda email=email: prepare_user_for_tests_via_api(ctx.env, email, DEFAULT_PASSWORD),
        )
        listeners.append((user["id"], email))
        logger.info(f"   слушатель {i + 1}/{ctx.count}: ID={user['id']}, {email} / {DEFAULT_PASSWORD}")

    content_ids = []

    logger.info("2. Tincan-курс...")
    archive_uuid = ctx.dry_or(
        "upload_archive(test_data/course_tincan.zip)",
        "00000000-0000-0000-0000-000000000001",
        lambda: tincan_ep.upload_archive("test_data/course_tincan.zip"),
    )
    tincan = tincan_ep.create(generate_tincan_payload(name=ctx.name("Tincan"), archive_uuid=archive_uuid))
    ctx.manifest.record("tincan", tincan["id"], "tincan.mass_delete([id])")
    content_ids.append(tincan["id"])

    logger.info("3. SCORM-курс...")
    scorm_uuid = ctx.dry_or(
        "upload_archive(test_data/test_lms_scorm_2004.zip)",
        "00000000-0000-0000-0000-000000000002",
        lambda: tincan_ep.upload_archive("test_data/test_lms_scorm_2004.zip"),
    )
    scorm = tincan_ep.create(generate_scorm_payload(name=ctx.name("Scorm"), archive_uuid=scorm_uuid))
    ctx.manifest.record("scorm", scorm["id"], "tincan.mass_delete([id])")
    content_ids.append(scorm["id"])

    logger.info("4. Практические задания (5-балльное, 10-балльное, зачёт/незачёт)...")
    hw5 = hw_ep.create(generate_homework_payload(name=ctx.name("HW5"), teacher_ids=[], inspector_ids=[]))
    ctx.manifest.record("homework_five_point", hw5["id"], "homework.mass_delete([id])")
    hw10 = hw10_ep.create(generate_homework_ten_point_payload(name=ctx.name("HW10"), teacher_ids=[], inspector_ids=[]))
    ctx.manifest.record("homework_ten_point", hw10["id"], "homework_ten_point.mass_delete([id])")
    hwpf = hwpf_ep.create(generate_homework_pass_fail_payload(name=ctx.name("HWPF"), teacher_ids=[], inspector_ids=[]))
    ctx.manifest.record("homework_pass_fail", hwpf["id"], "homework_pass_fail.mass_delete([id])")
    content_ids.extend([hw5["id"], hw10["id"], hwpf["id"]])

    logger.info("5. Тест (два вопроса) и опрос (один вопрос)...")
    test = tests_ep.create(generate_test_payload(name=ctx.name("Test")))
    ctx.manifest.record("test", test["id"], "tests.mass_delete([id])")
    for order in (1, 2):
        tests_ep.create_question(test["id"], generate_question_payload(order=order, text=f"Вопрос {order}"))
    poll = polls_ep.create(generate_poll_payload(name=ctx.name("Poll")))
    ctx.manifest.record("poll", poll["id"], "polls.mass_delete([id])")
    polls_ep.create_question(poll["id"], generate_question_payload(order=1, text="Вопрос опроса"))
    content_ids.extend([test["id"], poll["id"]])

    logger.info("6. LPD...")
    if ctx.env.name != "stage":
        logger.info(f"   {LPD_STAGE_ONLY_REASON} (окружение: {ctx.env.name})")
        ctx.manifest.skip("lpd", LPD_STAGE_ONLY_REASON)
    else:
        lpd = lpd_ep.create(generate_lpd_payload(lpd_id=get_next_lpd_id(), name=ctx.name("LPD")))
        ctx.manifest.record("lpd", lpd["id"], "lpd.mass_delete([id])")
        content_ids.append(lpd["id"])

    user_ids = [user_id for user_id, _ in listeners]
    logger.info(f"7. Назначение {len(content_ids)} активностей на инд. трек {len(user_ids)} слушателям...")
    ok = assignments_ep.assign_to_individual(content_ids, user_ids)
    if not ok:
        raise RuntimeError("assign-activities не принял назначение на инд. трек")
    # Запись о назначении вставляется в манифест сразу после слушателей, а не в конец:
    # --cleanup разбирает манифест с конца, и тогда активности удаляются ещё назначенными
    # (DELETE /content/{id} это допускает), а detach идёт после них. Если снимать назначение
    # первым, DELETE внешнего контента в ближайшие ~10 с отвечает 500 «Attempt to read
    # property "external_type" on null» (ContentObserver, develop 21.10.2026) — бэкенд ещё
    # разбирает detach; через 20 с удаляется штатно.
    entry = {"entity": "individual_assignment", "id": [content_ids, user_ids],
             "how_to_delete": "assignments.detach_from_individual(content_ids, user_ids)"}
    ctx.manifest.created.insert(len(user_ids), entry)
    logger.info(f"  + individual_assignment id={entry['id']} ({entry['how_to_delete']})")

    logger.info("Готово.")
    for user_id, email in listeners:
        logger.info(f"  слушатель {user_id}: {email} / {DEFAULT_PASSWORD} — {len(content_ids)} активностей в инд. треке")
