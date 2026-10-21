"""Сценарий tests: N тестов (type=test, по два вопроса single с верным/неверным ответом,
условие прохождения 60 %) — «голые» активности раздела «Тестирование», без программы/
потока/модуля. Для ручных проверок конструктора, назначения в модуль и прохождения
слушателем, когда целая цепочка activities избыточна. Опросы — сценарий polls.
"""
from api.endpoints.tests import TestsEndpoint
from api.helpers.data_generator import generate_question_payload, generate_test_payload
from utils.logger import logger

DESCRIPTION = "N тестов (по два вопроса, порог 60 %), без программы"
COUNT_HELP = "тестов"


def run(ctx) -> None:
    tests_ep = TestsEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        logger.info(f"Тест {i + 1}/{ctx.count} (два вопроса)...")
        test = tests_ep.create(generate_test_payload(name=ctx.name(f"Test{suffix}")))
        ctx.manifest.record("test", test["id"], "tests.mass_delete([id])")
        for order in (1, 2):
            tests_ep.create_question(test["id"], generate_question_payload(order=order, text=f"Вопрос {order}"))

    logger.info("Готово.")
