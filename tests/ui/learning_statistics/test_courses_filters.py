"""Фильтрация в разделе «Статистика обучения → Курсы» (docs/plans/statistics_courses_plan.md,
шаги 10, 15-17 — уровень UI; шаги 11-12 продублированы на уровне API в
tests/api/learning_statistics/test_courses_dashboard_filters.py, как размечено в плане).

Шаги 13-14 (фильтр по периоду/региону) НЕ покрыты: `DashboardsEndpoint` не поддерживает
эти фильтры (открытый вопрос №2 плана, требует доработки API-хелпера — вне роли
QA-теста, не гадаем и не добавляем новый параметр эндпоинта от себя).

Разведкой (одноразовый скрипт вне pytest) установлен порядок активации полей модалки
фильтра карточки курса: поле «Поток» становится доступным ТОЛЬКО после выбора значения в
поле «Программы» — выбора одного «Тип назначения: Программы» недостаточно (докстринг
`AdminCourseStatisticsPage._choose_in_filter` этот нюанс не уточняет).
"""
import allure
import pytest
from playwright.sync_api import expect

from api.helpers.data_generator import generate_stream_payload
from ui.pages.admin_dashboard_page import AdminDashboardPage, open_course_statistics_by_id


@allure.feature("Статистика обучения — Курсы")
@allure.story("Фильтрация")
class TestCoursesFilters:

    @allure.title("UI: поиск по названию курса в списке показывает только совпадающий курс")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_search_course_by_name(self, course_stats_admin_page, env, course_with_listeners):
        data = course_with_listeners(user_count=1)

        with allure.step("10. Найти курс по точному имени"):
            dashboard_page = AdminDashboardPage(course_stats_admin_page)
            dashboard_page.open_courses_dashboard(env.ui_base_url)
            row = dashboard_page.find_row(data["course_name"])
            expect(row).to_contain_text(data["course_name"])
            assert course_stats_admin_page.locator("table tbody tr").count() == 1

    @allure.title("UI: поиск по несуществующему названию курса — пустой список без ошибки")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_search_course_no_results(self, course_stats_admin_page, env, course_with_listeners):
        data = course_with_listeners(user_count=1)

        with allure.step("17. Поиск заведомо несуществующего курса — «Данные отсутствуют», без краша"):
            dashboard_page = AdminDashboardPage(course_stats_admin_page)
            dashboard_page.open_courses_dashboard(env.ui_base_url)
            dashboard_page.search(f"zzz_несуществующий_курс_{data['course_id']}_zzz")
            expect(course_stats_admin_page.get_by_text("Данные отсутствуют")).to_be_visible(timeout=15000)

    @allure.title("UI: фильтр карточки курса — disabled-поля, комбинация «Программа + Поток», сброс")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_map_filter_disabled_states_combo_and_reset(
        self, admin_page, env, streams_endpoint, course_with_listeners
    ):
        data = course_with_listeners(user_count=1)
        other_stream = streams_endpoint.create(data["program_id"], generate_stream_payload())

        with allure.step("Открыть карточку курса и фильтр карты"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            dialog = page.open_map_filter()

        with allure.step("10/13/14 preconditions. «Программы»/«Поток» задизейблены, пока не выбран тип"):
            assert not page.is_program_field_enabled(dialog)
            assert not page.is_stream_field_enabled(dialog)

        with allure.step("Выбор типа «Программы» включает поле «Программы», но не «Поток»"):
            page.set_assignment_types(dialog, page.TYPE_PROGRAMS)
            assert page.is_program_field_enabled(dialog)
            assert not page.is_stream_field_enabled(dialog), (
                "«Поток» должен оставаться недоступным, пока не выбрана «Программа»"
            )

        with allure.step("16. Выбор программы включает «Поток»; фильтр на СВОЙ поток не меняет данные"):
            page.select_program(dialog, data["program_name"])
            assert page.is_stream_field_enabled(dialog)
            page.select_stream(dialog, data["stream_name"])
            page.apply_filter(dialog)
            totals_own_stream = page.read_map_totals()
            assert totals_own_stream["Слушателей"]["value"] == "1"

        with allure.step("Фильтр на ЧУЖОЙ поток той же программы обнуляет данные (узкая выборка)"):
            # Перезагружаем карточку курса заново (а не переиспользуем ту же модалку
            # повторно) — разведкой поймана нестабильность повторного выбора значения в
            # уже применённом мультиселекте "Поток" (открытое меню не появлялось у
            # переиспользуемой модалки, вероятно из-за уже выставленного чипа).
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            dialog2 = page.open_map_filter()
            page.set_assignment_types(dialog2, page.TYPE_PROGRAMS)
            page.select_program(dialog2, data["program_name"])
            page.select_stream(dialog2, other_stream["attributes"]["name"])
            page.apply_filter(dialog2)
            totals_other_stream = page.read_map_totals()
            assert totals_other_stream["Слушателей"]["value"] == "0"

        with allure.step("15. Сброс фильтра возвращает полные данные курса"):
            dialog3 = page.open_map_filter()
            page.reset_filter(dialog3)
            # reset_filter не ждёт ответ бэкенда (в отличие от apply_filter, где ожидание
            # скрытия диалога совпадает по времени с завершением запроса) — read_map_totals
            # само по себе не гарантирует свежих данных, если в подписи уже была цифра
            # (её wait на "цифра в тексте" проходит мгновенно на уже отрисованном "0" от
            # предыдущего фильтра). Поэтому опрашиваем несколько секунд, а не читаем один раз.
            totals_after_reset = page.read_map_totals()
            for _ in range(10):
                if totals_after_reset["Слушателей"]["value"] == "1":
                    break
                admin_page.wait_for_timeout(1000)
                totals_after_reset = page.read_map_totals()
            assert totals_after_reset["Слушателей"]["value"] == "1"
