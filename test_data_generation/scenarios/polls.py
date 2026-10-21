"""Сценарий polls: N опросов (type=poll, один вопрос single — для опросов вопрос обязан
быть привязан к группе, generate_question_payload это делает) без программы/потока/
модуля. Тесты — сценарий tests, анкеты обратной связи — aos.
"""
from api.endpoints.polls import PollsEndpoint
from api.helpers.data_generator import generate_poll_payload, generate_question_payload
from utils.logger import logger

DESCRIPTION = "N опросов (один вопрос), без программы"
COUNT_HELP = "опросов"


def run(ctx) -> None:
    polls_ep = PollsEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        logger.info(f"Опрос {i + 1}/{ctx.count} (один вопрос)...")
        poll = polls_ep.create(generate_poll_payload(name=ctx.name(f"Poll{suffix}")))
        ctx.manifest.record("poll", poll["id"], "polls.mass_delete([id])")
        polls_ep.create_question(poll["id"], generate_question_payload(order=1, text="Вопрос опроса"))

    logger.info("Готово.")
