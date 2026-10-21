"""Сценарий lpd: N активностей LPD (ЛПД) без программы/потока. Как и шаг LPD внутри
activities, выполняется только при --env stage (tests/api/create_activity/lpd помечены
маркером env("stage") — на develop модуля нет); на остальных окружениях шаг пишется в
манифест как skipped с причиной, а не падает.
"""
from api.endpoints.lpd import LpdEndpoint
from api.helpers.data_generator import generate_lpd_payload, get_next_lpd_id
from utils.logger import logger

from scenarios.activities import LPD_STAGE_ONLY_REASON

DESCRIPTION = "N активностей LPD (ЛПД), без программы — только на stage"
COUNT_HELP = "активностей LPD"


def run(ctx) -> None:
    if ctx.env.name != "stage":
        logger.info(f"{LPD_STAGE_ONLY_REASON} (окружение: {ctx.env.name})")
        ctx.manifest.skip("lpd", LPD_STAGE_ONLY_REASON)
        return

    lpd_ep = LpdEndpoint(ctx.api_client)
    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        logger.info(f"LPD {i + 1}/{ctx.count}...")
        lpd = lpd_ep.create(generate_lpd_payload(lpd_id=get_next_lpd_id(), name=ctx.name(f"LPD{suffix}")))
        ctx.manifest.record("lpd", lpd["id"], "lpd.mass_delete([id])")

    logger.info("Готово.")
