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

    def get_course_map(self, course_id: int, date_from: str = "2000-01-01", date_to: str = "2100-01-01") -> list:
        """Данные интерактивной карты курса — список по всем регионам РФ (не только тем,
        где есть слушатели): [{"region": {"region_name": "...", "region_code": "000000NNN"},
        "data": {"total_count": int, "passed_count": int, "launched_count": int,
        "not_started": int}}, ...]. `region_code` — тот же 9-значный код с ведущими
        нулями, что атрибут data-region-id у <path> на SVG-карте
        (ui.pages.admin_dashboard_page.AdminCourseStatisticsPage.region(code=...)) —
        удобно сверять с UI по нему, а не по названию региона.

        Даты по умолчанию — широкий диапазон "с запасом", а не текущая неделя (как
        в дефолте UI-виджета), чтобы не зависеть от того, когда именно был прогон теста."""
        params = urlencode({"date_from": date_from, "date_to": date_to})
        resp = self.client.get(f"/statistics/courses/{course_id}/map?{params}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def get_course_users(self, course_id: int, page: int = 1, per_page: int = 25) -> list:
        """Строки итоговой таблицы слушателей курса (тот же источник данных, что и
        AdminCourseStatisticsPage.listener_table_rows, но с полями API, не заголовками
        UI): user_id, full_name, email, state (0 — не начато/назначено, 1 — в процессе —
        нумерация подтверждена эмпирически, не задокументирована бэкендом), launched_at,
        finished_at, completion_time_in_minutes, source, current_child, passed_percent.

        current_child и passed_percent бэкенд считает, но в таблицу UI не выводит (см.
        докстринг AdminCourseStatisticsPage) — тем не менее полезны для API-уровня проверок."""
        params = urlencode({"page": page, "per-page": per_page})
        resp = self.client.get(f"/statistics/courses/{course_id}/users?{params}")
        expect_status(resp, 200)
        return resp.json().get("data", [])
