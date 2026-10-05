"""Сценарий demo: наполнить стенд для демо — users + program_full + activities +
certificates + banner_and_partners с малым N. Переиспользует run() остальных сценариев
напрямую (без копипасты кода), выставляя каждому под-сценарию ctx.count=1; манифест
общий (dataclasses.replace копирует ссылку на тот же объект Manifest), поэтому все
созданные сущности попадают в один итоговый манифест и один --cleanup.
"""
from dataclasses import replace

from utils.logger import logger

from scenarios import activities, banner_and_partners, certificates, program_full, users

DESCRIPTION = ("демо-наполнение стенда: users + program_full + activities + certificates + "
               "banner_and_partners (count=1 на каждый шаг)")

SUB_SCENARIOS = (
    ("users", users),
    ("program_full", program_full),
    ("activities", activities),
    ("certificates", certificates),
    ("banner_and_partners", banner_and_partners),
)


def run(ctx) -> None:
    sub_ctx = replace(ctx, count=1)

    for name, module in SUB_SCENARIOS:
        logger.info(f"=== demo: {name} ===")
        module.run(sub_ctx)

    logger.info("Готово: стенд наполнен для демо.")
