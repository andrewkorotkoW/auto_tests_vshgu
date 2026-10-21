"""Сценарий homework: N практических заданий каждого типа оценки — 5-балльное,
10-балльное и зачёт/незачёт (три разных эндпоинта api/endpoints/homework*.py, один и тот же
POST /content с разным grade_type), без программы/потока. Преподаватель и проверяющий не
назначаются (teacher_ids/inspector_ids пустые) — как в сценарии activities.
"""
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.homework_pass_fail import HomeworkPassFailEndpoint
from api.endpoints.homework_ten_point import HomeworkTenPointEndpoint
from api.helpers.data_generator import (
    generate_homework_pass_fail_payload,
    generate_homework_payload,
    generate_homework_ten_point_payload,
)
from utils.logger import logger

DESCRIPTION = "N практических заданий каждого типа (5-балльное / 10-балльное / зачёт-незачёт), без программы"
COUNT_HELP = "заданий каждого из трёх типов оценки"


def run(ctx) -> None:
    hw_ep = HomeworkEndpoint(ctx.api_client)
    hw10_ep = HomeworkTenPointEndpoint(ctx.api_client)
    hwpf_ep = HomeworkPassFailEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""

        logger.info(f"ДЗ (5-балльное) {i + 1}/{ctx.count}...")
        hw5 = hw_ep.create(generate_homework_payload(name=ctx.name(f"HW5{suffix}"), teacher_ids=[], inspector_ids=[]))
        ctx.manifest.record("homework_five_point", hw5["id"], "homework.mass_delete([id])")

        logger.info(f"ДЗ (10-балльное) {i + 1}/{ctx.count}...")
        hw10 = hw10_ep.create(generate_homework_ten_point_payload(
            name=ctx.name(f"HW10{suffix}"), teacher_ids=[], inspector_ids=[],
        ))
        ctx.manifest.record("homework_ten_point", hw10["id"], "homework_ten_point.mass_delete([id])")

        logger.info(f"ДЗ (зачёт/незачёт) {i + 1}/{ctx.count}...")
        hwpf = hwpf_ep.create(generate_homework_pass_fail_payload(
            name=ctx.name(f"HWPF{suffix}"), teacher_ids=[], inspector_ids=[],
        ))
        ctx.manifest.record("homework_pass_fail", hwpf["id"], "homework_pass_fail.mass_delete([id])")

    logger.info("Готово.")
