import time
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def retry_until_success(
    func: Callable[[], T],
    *,
    timeout: float = 15,
    interval: float = 1,
    success_codes: Iterable[int] = (200, 201, 204),
) -> T:
    """Повторяет func() (обычно HTTP-запрос), пока он не вернёт success_codes или не истечёт timeout.

    Используется вместо слепой паузы там, где у бэкенда нет отдельного статус-эндпоинта
    для отслеживания асинхронной индексации (например, назначение контента в модуль перед
    последующим назначением пользователей) — ждём готовности, повторяя саму целевую операцию.
    """
    deadline = time.monotonic() + timeout
    result = func()
    while getattr(result, "status_code", None) not in success_codes and time.monotonic() < deadline:
        time.sleep(interval)  # интервал между повторами реальной операции, не слепая пауза перед ней
        result = func()
    return result


def wait_until(predicate: Callable[[], bool], *, timeout: float = 15, interval: float = 3) -> bool:
    """Опрашивает predicate(), пока он не вернёт True или не истечёт timeout.

    В отличие от retry_until_success (ждёт успешного статуса конкретного запроса),
    здесь predicate — произвольное условие (например «сущность пропала из списка»)
    для асинхронных операций без отдельного статус-эндпоинта. Возвращает финальный
    результат predicate(): False, если условие не выполнилось за timeout — вызывающий
    код сам решает, считать это ошибкой или xfail-кандидатом в дефект.
    """
    deadline = time.monotonic() + timeout
    result = predicate()
    while not result and time.monotonic() < deadline:
        time.sleep(interval)
        result = predicate()
    return result
