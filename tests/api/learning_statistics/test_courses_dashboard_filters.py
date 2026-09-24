"""API-уровень фильтрации статистики курсов (docs/plans/statistics_courses_plan.md,
шаги 11-12 — план размечает их как «Уровень: API»). UI-уровень фильтрации (шаги 10,
15-17) — в tests/ui/learning_statistics/test_courses_filters.py.

Шаги 13-14 (фильтр по периоду/региону) не покрыты нигде: `DashboardsEndpoint` не
поддерживает эти параметры (открытый вопрос №2 плана) — доработка самого API-хелпера
вне роли QA-теста.
"""
from urllib.parse import urlencode

import allure
import pytest

from api.helpers.data_generator import generate_stream_payload
from api.helpers.expectations import expect_status


@allure.feature("Статистика обучения — Курсы")
@allure.story("Фильтрация (API)")
class TestCoursesDashboardApiFilters:

    @allure.title("API: фильтр по потоку сужает строку статистики курса до нужного stream_id")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.statistics
    def test_get_course_row_filters_by_stream_id(self, streams_endpoint, dashboards_endpoint, course_with_listeners):
        data = course_with_listeners(user_count=1)
        other_stream = streams_endpoint.create(data["program_id"], generate_stream_payload())

        with allure.step("11. Строка курса находится по своему потоку"):
            row = dashboards_endpoint.get_course_row(data["course_name"], data["stream_id"])
            assert row is not None
            assert row["total"] == 1

        with allure.step("Строка НЕ находится по чужому потоку той же программы"):
            row_other = dashboards_endpoint.get_course_row(data["course_name"], other_stream["id"])
            assert row_other is None

    @allure.title("API: фильтр filters[type][]=programs находит курс, назначенный через поток программы")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.statistics
    def test_get_course_row_type_programs_filter(self, api_client, course_with_listeners):
        data = course_with_listeners(user_count=1)

        with allure.step("12. filters[type][]=programs находит курс"):
            params = urlencode(
                [
                    ("filters[name]", data["course_name"]),
                    ("filters[type][]", "programs"),
                    ("filters[stream_id][]", data["stream_id"]),
                    ("per-page", 10),
                    ("page", 1),
                ]
            )
            resp = api_client.get(f"/statistics/courses/?{params}")
            expect_status(resp, 200)
            names = [item["name"] for item in resp.json().get("data", [])]
            assert data["course_name"] in names

        with allure.step(
            "filters[type][]=individual: курс всё ещё в списке (найден по имени), но с "
            "нулевыми показателями — назначения через поток программы в подсчёт "
            "инд. трека не попадают. Открытие: filters[type][] не исключает строку курса "
            "из выдачи (курс, найденный по filters[name], остаётся в data[]) — он только "
            "переключает, ПО КАКОМУ ТИПУ НАЗНАЧЕНИЙ считаются агрегаты total/not_started/"
            "passed/... в этой строке (изначально предполагалось, что несовпадающий тип "
            "уберёт курс из выдачи целиком — разведкой на develop это не подтвердилось)."
        ):
            params_individual = urlencode(
                [
                    ("filters[name]", data["course_name"]),
                    ("filters[type][]", "individual"),
                    ("per-page", 10),
                    ("page", 1),
                ]
            )
            resp2 = api_client.get(f"/statistics/courses/?{params_individual}")
            expect_status(resp2, 200)
            items2 = {item["name"]: item for item in resp2.json().get("data", [])}
            assert data["course_name"] in items2
            assert items2[data["course_name"]]["total"] == 0
