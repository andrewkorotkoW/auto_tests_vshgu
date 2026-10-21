"""Сценарий tests_polls: N тестов (type=test, по два вопроса single с верным/неверным
ответом, условие прохождения 60 %) и N опросов (type=poll, один вопрос) — «голые»
активности раздела «Тестирование», без программы/потока/модуля. Нужны для ручных
проверок конструктора, назначения в модуль и прохождения слушателем, когда целая
цепочка activities избыточна.
"""
from api.endpoints.polls import PollsEndpoint
from api.endpoints.tests import TestsEndpoint
from api.helpers.data_generator import generate_poll_payload, generate_question_payload, generate_test_payload
from utils.logger import logger

DESCRIPTION = "N тестов (по два вопроса) + N опросов (один вопрос), без программы"
COUNT_HELP = "тестов и опросов (по N тех и других)"


def run(ctx) -> None:
    tests_ep = TestsEndpoint(ctx.api_client)
    polls_ep = PollsEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""

        logger.info(f"Тест {i + 1}/{ctx.count} (два вопроса)...")
        test = tests_ep.create(generate_test_payload(name=ctx.name(f"Test{suffix}")))
        ctx.manifest.record("test", test["id"], "tests.mass_delete([id])")
        for order in (1, 2):
            tests_ep.create_question(test["id"], generate_question_payload(order=order, text=f"Вопрос {order}"))

        logger.info(f"Опрос {i + 1}/{ctx.count} (один вопрос)...")
        poll = polls_ep.create(generate_poll_payload(name=ctx.name(f"Poll{suffix}")))
        ctx.manifest.record("poll", poll["id"], "polls.mass_delete([id])")
        polls_ep.create_question(poll["id"], generate_question_payload(order=1, text="Вопрос опроса"))

    logger.info("Готово.")
