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
