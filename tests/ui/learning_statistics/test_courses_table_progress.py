"""Карточка курса — таблица слушателей: прогресс прохождения (шаги 19-21 плана).

Разведкой (одноразовые скрипты вне pytest, не сохранены в репозитории) установлено
ограничение более жёсткое, чем предполагал план: `AssignmentsEndpoint.change_state` на
этом стенде принимает ТОЛЬКО state=2 (CONTENT_STATE_PASSED) — state=0/1/3/4 отклоняются
с 422 "Выбранное значение для state ошибочно" (включая сам CONTENT_STATE_LAUNCHED=1 из
api/endpoints/assignments.py). То есть допущенный планом API-уровневый обход для статуса
«в процессе» (шаг 19) на практике недоступен, а реальное UI-прохождение курса Tincan
сейчас блокировано двумя независимыми задокументированными дефектами стенда:
нераскрывающийся шеврон модуля в потоке
(tests/ui/courses/tincan/stream/test_user_tincan_flow.py, xfail) и не отображающийся
назначенный курс в инд. треке
(tests/ui/courses/tincan/individual/test_user_tincan_individual_flow.py, xfail).

Переход в state=2 (шаг 20 — «пройдено», % обновляется) РАБОТАЕТ и обновляется быстро
(разведкой — около 2с на количество слушателей/статус курса, в отличие от
задокументированного 120-секундного лага полей passed/assignments_passed на дашборде
программ/курсов в tests/ui/dashboards) — покрыт обычным (не xfail) тестом.

Шаг 21 («Время прохождения, мин» с допуском) тоже оформлен xfail: переход в state=2
напрямую (без реального launched_at от UI-плеера) оставляет `completion_time_in_minutes`
пустым — «Время прохождения мин» в таблице остаётся «0 мин» даже после «Пройдено»
(подтверждено разведкой). Содержательное значение появляется только при реальном
прохождении в UI-плеере, заблокированном теми же двумя дефектами, что и шаг 19.
"""
import allure
import pytest
from playwright.sync_api import expect

from api.endpoints.assignments import CONTENT_STATE_LAUNCHED, CONTENT_STATE_PASSED
from ui.pages.admin_dashboard_page import open_course_statistics_by_id


def _wait_listener_row(admin_page, page, user_id):
    first_id_cell = admin_page.locator(".courses-statistic-table table tbody tr td").first
    expect(first_id_cell).to_contain_text(str(user_id), timeout=20000)
    return page.listener_table_rows()[0]


def _assignment_id_for(assignments_endpoint, data, user_id):
    stream_assignments = assignments_endpoint.list_for_stream(
        data["program_id"], data["stream_id"], [data["stream_content_id"]]
    )
    return next(int(i["assignment_id"]) for i in stream_assignments if int(i["user_id"]) == user_id)


@allure.feature("Статистика обучения — Курсы")
@allure.story("Таблица — прогресс прохождения")
class TestCoursesTableProgress:

    @allure.title("API: перевод назначения в статус «в процессе» недоступен на develop")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.statistics
    @pytest.mark.xfail(
        reason=(
            "19. AssignmentsEndpoint.change_state(state=CONTENT_STATE_LAUNCHED=1) отвечает "
            "422 'Выбранное значение для state ошибочно' — этот API-путь к статусу «в "
            "процессе» на develop не работает, хотя сама константа CONTENT_STATE_LAUNCHED "
            "объявлена в api/endpoints/assignments.py (подтверждено разведкой: state=0/1/3/4 "
            "все отклонены 422, принимается только state=2). Альтернативный путь — реальное "
            "прохождение курса в UI слушателем — заблокирован двумя уже задокументированными "
            "дефектами стенда: нераскрывающийся шеврон модуля в потоке "
            "(tests/ui/courses/tincan/stream/test_user_tincan_flow.py) и не отображающийся "
            "назначенный курс в инд. треке "
            "(tests/ui/courses/tincan/individual/test_user_tincan_individual_flow.py). Третьего "
            "пути к статусу «в процессе» сейчас нет."
        ),
        strict=False,
    )
    def test_status_in_progress_via_api(self, course_with_listeners, assignments_endpoint):
        data = course_with_listeners(user_count=1)
        user_id = data["users"][0]["id"]
        assignment_id = _assignment_id_for(assignments_endpoint, data, user_id)

        assignments_endpoint.change_state(
            user_id=user_id,
            assignment_id=assignment_id,
            stream_content_id=data["stream_content_id"],
            state=CONTENT_STATE_LAUNCHED,
        )

    @allure.title("API+UI: статус «пройдено» и прогресс 100% после смены статуса назначения")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_status_passed_updates_after_change_state(
        self, admin_page, env, course_with_listeners, assignments_endpoint, dashboards_endpoint
    ):
        data = course_with_listeners(user_count=1)
        user = data["users"][0]
        assignment_id = _assignment_id_for(assignments_endpoint, data, user["id"])

        with allure.step("20. Перевести назначение в «Пройдено» через API"):
            assignments_endpoint.change_state(
                user_id=user["id"],
                assignment_id=assignment_id,
                stream_content_id=data["stream_content_id"],
                state=CONTENT_STATE_PASSED,
            )
            course_row = dashboards_endpoint.wait_for_course_row(
                data["course_name"], data["stream_id"],
                predicate=lambda row: row.get("passed", 0) >= 1,
                timeout=60,
            )
            assert course_row["passed"] == 1
            assert course_row["passed_percentage"] == 100

        with allure.step("Карточка курса: статус «Пройдено», прогресс 100%"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            row = _wait_listener_row(admin_page, page, user["id"])
            assert row["Статус курса"] == "Пройдено"
            assert row["Прогресс курса %"] == "100%"

    @allure.title("UI: «Время прохождения, мин» не заполняется без реального прохождения курса")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.ui
    @pytest.mark.statistics
    @pytest.mark.xfail(
        reason=(
            "21. change_state(state=CONTENT_STATE_PASSED) напрямую (без реального launched_at "
            "от UI-плеера) оставляет completion_time_in_minutes пустым — «Время прохождения "
            "мин» в таблице остаётся «0 мин» вместо содержательного значения (подтверждено "
            "разведкой). Сравнение с допуском ±N минут, заложенное в план, имеет смысл только "
            "при реальном прохождении курса слушателем в UI, которое заблокировано тем же "
            "дефектом шеврона, что и шаг 19 (см. test_status_in_progress_via_api выше и "
            "tests/ui/courses/tincan/stream/test_user_tincan_flow.py)."
        ),
        strict=False,
    )
    def test_completion_time_reflects_real_duration(
        self, admin_page, env, course_with_listeners, assignments_endpoint
    ):
        data = course_with_listeners(user_count=1)
        user = data["users"][0]
        assignment_id = _assignment_id_for(assignments_endpoint, data, user["id"])

        assignments_endpoint.change_state(
            user_id=user["id"],
            assignment_id=assignment_id,
            stream_content_id=data["stream_content_id"],
            state=CONTENT_STATE_PASSED,
        )

        page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
        page.read_map_totals()
        row = _wait_listener_row(admin_page, page, user["id"])
        actual_minutes = int(row["Время прохождения мин"].split()[0])
        assert actual_minutes > 0, (
            "«Время прохождения мин» должно отражать реальную длительность прохождения, "
            f"а не оставаться нулевым (получено: {row['Время прохождения мин']!r})"
        )
