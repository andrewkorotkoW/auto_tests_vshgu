import time
from typing import Callable, Dict, Optional
from urllib.parse import urlencode

from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class DashboardsEndpoint:
    """Статистика дашбордов программ и курсов (/admin/learning-statistics/*)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def get_program_row(self, program_name: str) -> Optional[Dict]:
        """Строка статистики программы по имени, либо None, если ещё не появилась
        (статистика считается асинхронно после назначений/прохождений)."""
        params = urlencode({"filters[name]": program_name, "per-page": 10, "page": 1})
        resp = self.client.get(f"/statistics/programs/?{params}")
        expect_status(resp, 200)
        for item in resp.json().get("data", []):
            if item.get("name") == program_name:
                return item
        logger.info(f"В статистике программ пока не найдена программа {program_name}")
        return None

    def get_course_row(self, course_name: str, stream_id: int) -> Optional[Dict]:
        """Строка статистики курса по имени и потоку, либо None, если ещё не появилась."""
        params = urlencode(
            [
                ("filters[name]", course_name),
                ("filters[type][]", "programs"),
                ("filters[stream_id][]", stream_id),
                ("per-page", 10),
                ("page", 1),
            ]
        )
        resp = self.client.get(f"/statistics/courses/?{params}")
        expect_status(resp, 200)
        for item in resp.json().get("data", []):
            if item.get("name") == course_name:
                return item
        logger.info(f"В статистике курсов пока не найден курс {course_name}")
        return None

    def wait_for_program_row(
        self,
        program_name: str,
        predicate: Optional[Callable[[Dict], bool]] = None,
        timeout: float = 90,
        interval: float = 3,
    ) -> Dict:
        """Дождаться строки статистики программы: она считается асинхронно после
        назначений/смены статусов прохождения, поэтому сразу после подготовки
        данных строки может ещё не быть (или значения в ней не финальные —
        для этого случая передайте predicate)."""
        deadline = time.monotonic() + timeout
        row = self.get_program_row(program_name)
        while (row is None or (predicate and not predicate(row))) and time.monotonic() < deadline:
            time.sleep(interval)
            row = self.get_program_row(program_name)
        if row is None:
            raise AssertionError(f"Статистика программы {program_name} не появилась за {timeout}s")
        return row

    def wait_for_course_row(
        self,
        course_name: str,
        stream_id: int,
        predicate: Optional[Callable[[Dict], bool]] = None,
        timeout: float = 90,
        interval: float = 3,
    ) -> Dict:
        """Дождаться строки статистики курса (см. wait_for_program_row)."""
        deadline = time.monotonic() + timeout
        row = self.get_course_row(course_name, stream_id)
        while (row is None or (predicate and not predicate(row))) and time.monotonic() < deadline:
            time.sleep(interval)
            row = self.get_course_row(course_name, stream_id)
        if row is None:
            raise AssertionError(f"Статистика курса {course_name} не появилась за {timeout}s")
        return row
