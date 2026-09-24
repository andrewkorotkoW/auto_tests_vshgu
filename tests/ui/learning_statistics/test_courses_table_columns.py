"""Карточка курса — итоговая таблица слушателей, состав столбцов и значения ячеек
(docs/plans/statistics_courses_plan.md, шаг 18).

Плановый пункт явно помечен «требует ручной сверки с ДТТ владельцем»: полного списка
столбцов из ДТТ п.3.2.2 в репозитории нет, поэтому тест НЕ сверяет состав столбцов с
внешним документом — он фиксирует то, что фактически рендерит develop для курса Tincan
с разделами (test_data/course_tincan.zip, тот же курс, что эталонный id=4393, см.
docs/plans/statistics_courses_stand_facts.md), и падает, если состав/порядок/подписи
изменятся — то есть работает как регрессионный снимок, а не как сверка с ДТТ.

Важно: `AdminCourseStatisticsPage.listener_table_columns/rows()` не ждут отдельно XHR
итоговой таблицы (в отличие от `read_map_totals`, где ожидание встроено) — сразу после
навигации таблица может быть ещё не перерисована с реальными данными. Тест ждёт явно
через `expect()` на первую ячейку ID перед чтением столбцов/строк — без этого ожидания
разведкой поймана гонка (таблица читалась с кратким «переходным» состоянием и всего
8 столбцами вместо 9+1).
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_dashboard_page import open_course_statistics_by_id


EXPECTED_COLUMNS_WITH_SECTIONS = [
    "ID",
    "ФИО",
    "Email",
    "Статус курса",
    "Тип назначения",
    "Дата начала обучения по курсу",
    "Дата завершения последнего пройденного раздела",
    "Текущий раздел",
    "Прогресс курса %",
    "Время прохождения мин",
    "",
]


@allure.feature("Статистика обучения — Курсы")
@allure.story("Таблица — столбцы")
class TestCoursesTableColumns:

    @allure.title("UI: состав и порядок столбцов итоговой таблицы курса с разделами")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_listener_table_columns_for_course_with_sections(self, admin_page, env, course_with_listeners):
        data = course_with_listeners(user_count=1)

        with allure.step("18. Открыть карточку курса и дождаться таблицы слушателей"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            first_id_cell = admin_page.locator(".courses-statistic-table table tbody tr td").first
            expect(first_id_cell).to_contain_text(str(data["users"][0]["id"]), timeout=20000)

        with allure.step("Состав и порядок столбцов совпадают с фактическим develop"):
            assert page.listener_table_columns() == EXPECTED_COLUMNS_WITH_SECTIONS

    @allure.title("UI: свеженазначенный, не начавший курс слушатель — пустые значения прогресса")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_listener_row_for_freshly_assigned_user(self, admin_page, env, course_with_listeners):
        data = course_with_listeners(user_count=1)
        user = data["users"][0]

        with allure.step("Открыть карточку курса и дождаться строки слушателя"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            first_id_cell = admin_page.locator(".courses-statistic-table table tbody tr td").first
            expect(first_id_cell).to_contain_text(str(user["id"]), timeout=20000)

        with allure.step("18. «Назначено»: пустая дата начала, прогресс 0%, прочерк в «Текущий раздел»"):
            rows = page.listener_table_rows()
            assert len(rows) == 1
            row = rows[0]
            assert row["ID"] == str(user["id"])
            assert row["Статус курса"] == "Назначено"
            assert row["Дата начала обучения по курсу"] == ""
            assert row["Текущий раздел"] == "—"
            assert row["Прогресс курса %"] == "0%"
            assert row["Время прохождения мин"] == "0 мин"
