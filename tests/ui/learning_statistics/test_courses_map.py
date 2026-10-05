"""Карточка курса в статистике обучения (/admin/learning-statistics/courses/{id}/info):
интерактивная карта — общий вид (docs/plans/statistics_courses_plan.md, шаги 1-9).

Разведкой перед написанием тестов (одноразовые скрипты вне pytest, не сохранены в
репозитории) установлено два факта, которые сужают то, что вообще можно проверить
через DOM:

1. Регион слушателя на карте курса не определяется ни `region_id`/`municipality_id`
   пользователя, ни регионом модуля (см. уже закрытый открытый вопрос №1 плана,
   докстринг `AdminCourseStatisticsPage`) — во всех прогонах разведки (3 независимых
   курса, разные пользователи) регион с данными стабильно один и тот же. Получить на
   develop двух слушателей в РАЗНЫХ регионах контролируемо нельзя — тесты читают
   регион(ы) с данными из `DashboardsEndpoint.get_course_map`, а не подставляют
   конкретное название региона.
2. Цвет заливки `<path>` региона на карте (`getComputedStyle(el).fill`) ОДИНАКОВЫЙ у
   региона с данными и у региона без данных (rgb(69, 172, 225) в обоих случаях, разведка
   на живом курсе с 1 назначенным слушателем) — никакого CSS-класса/атрибута,
   зависящего от % прохождения, кроме `vs-interactive-map__region_selected`
   (появляется только по клику), в вёрстке нет. Поэтому «регион подсвечен» /
   «разная интенсивность цвета» (шаги 5-6 плана) через DOM не проверяются вовсе — это
   тот же класс ограничения, что и задокументированное в плане «не автоматизируем:
   цвет по пикселям», только выявленный без скриншотов. Вместо этого шаги 4-6
   проверяются по фактически связанным с данными вещам: цифры на диаграммах, состояние
   «Данные отсутствуют» без слушателей, работоспособность выбора региона (клик →
   класс _selected, смена вкладок, % от общего), совпадение вкладки «Таблица» с API.
3. Тултип региона (наведение) — шаг 7 — не покрыт: `hover()` виснет в бесконечном
   ретрае actionability (тот же самый перехват точки клика соседним регионом/тулбаром,
   что уже описан для `toggle_region` в Page Object), обходной `dispatch_event
   ('mouseover')` действительно создаёт элемент `[class*='tooltip']`, но он невидим и
   с пустым текстом — надёжного локатора для содержимого тултипа разведкой найти не
   удалось. Требует отдельной UI-разведки (в идеале — от t2, с доступом к вёрстке).
   Шаг 8 (drill-down по клику) в плане прямо помечен «требует ручной сверки с ДТТ» —
   не покрываем согласно этой пометке.
"""
import allure
import pytest

from ui.pages.admin_dashboard_page import AdminDashboardPage, open_course_statistics_by_id


@allure.feature("Статистика обучения — Курсы")
@allure.story("Карта — общий вид")
class TestCoursesMapOverview:

    @allure.title("UI: курс без слушателей — карта и таблица показывают «данных нет»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_course_without_listeners_shows_empty_state(self, admin_page, env, course_without_listeners):
        with allure.step("1-2. Открыть карточку статистики курса без слушателей"):
            page = open_course_statistics_by_id(
                admin_page, env, course_without_listeners["course_id"], use_global_domain=True
            )

        with allure.step("3-4. Карта присутствует, диаграммы нулевые, ни один регион не выбран"):
            from playwright.sync_api import expect

            expect(admin_page.locator("svg.vs-interactive-map")).to_be_visible(timeout=15000)
            expect(admin_page.get_by_text("Данные отсутствуют").first).to_be_visible(timeout=15000)
            assert page.map_tab_names() == ["ВСЕГО"], "Без выбранного региона должна быть только вкладка «Всего»"
            assert page.selected_region_names() == [], "Без слушателей ни один регион не должен быть выбран"

    @allure.title("UI: курс со слушателями — диаграммы карты совпадают со значениями API")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_course_with_listeners_map_matches_api(
        self, course_stats_admin_page, env, course_with_listeners, dashboards_endpoint
    ):
        data = course_with_listeners(user_count=2)

        with allure.step("1. Открыть карточку курса из списка"):
            dashboard_page = AdminDashboardPage(course_stats_admin_page)
            dashboard_page.open_courses_dashboard(env.ui_base_url)
            course_page = dashboard_page.open_course_statistics(data["course_name"])

        with allure.step("2-3. Карта отрисована, диаграммы «Всего» совпадают с числом назначенных"):
            totals = course_page.read_map_totals()
            assert totals["Слушателей"]["value"] == "2"
            assert totals["Назначено"]["value"] == "2"
            assert totals["Завершили курс"]["value"] == "0"
            assert course_page.map_tab_names() == ["ВСЕГО"]

        with allure.step("5. Определить регион(ы) с данными через API и выбрать его на карте"):
            course_map = dashboards_endpoint.get_course_map(data["course_id"])
            regions_with_data = [r for r in course_map if r["data"]["total_count"] > 0]
            assert regions_with_data, "API карты курса не вернул ни одного региона с данными"
            region_code = regions_with_data[0]["region"]["region_code"]
            region_name = regions_with_data[0]["region"]["region_name"]
            api_region_data = regions_with_data[0]["data"]

            assert not course_page.is_region_selected(code=region_code)
            course_page.toggle_region(code=region_code)
            assert course_page.is_region_selected(code=region_code), (
                f"Регион {region_name} ({region_code}) не получил класс "
                "vs-interactive-map__region_selected после клика"
            )
            assert course_page.selected_region_names() == [region_name]

        with allure.step("6. При выбранном регионе вкладка меняется на «Графики»/«Таблица», % считается от общего"):
            assert course_page.map_tab_names() == ["ГРАФИКИ", "ТАБЛИЦА"]
            totals_selected = course_page.read_map_totals()
            assert totals_selected["Слушателей"]["value"] == str(api_region_data["total_count"])
            assert totals_selected["Слушателей"]["percent"] == "100.00%", (
                "Единственный регион с данными должен давать 100% от общего числа слушателей"
            )

        with allure.step("Вкладка «Таблица» региона совпадает с данными API карты"):
            course_page.open_map_tab("Таблица")
            rows = course_page.read_region_table_rows()
            assert len(rows) == 1
            row = rows[0]
            assert row["Регион"] == region_name
            assert row["Слушателей"] == str(api_region_data["total_count"])
            assert row["Назначено"] == str(api_region_data["total_count"])
            assert row["Завершили курс"] == str(api_region_data["passed_count"])

        with allure.step("Повторный клик снимает выбор — карта возвращается к вкладке «Всего»"):
            course_page.toggle_region(code=region_code)
            assert not course_page.is_region_selected(code=region_code)
            assert course_page.selected_region_names() == []
            assert course_page.map_tab_names() == ["ВСЕГО"]

    @allure.title("UI: переключение между курсами обновляет карту (не остаются данные предыдущего)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_switching_course_updates_map(self, admin_page, env, course_with_listeners):
        course_a = course_with_listeners(user_count=1)
        course_b = course_with_listeners(user_count=2)

        with allure.step("9. Открыть карту курса A, затем курса B — значения должны обновиться"):
            page_a = open_course_statistics_by_id(admin_page, env, course_a["course_id"], use_global_domain=True)
            totals_a = page_a.read_map_totals()
            assert totals_a["Слушателей"]["value"] == "1"

            page_b = open_course_statistics_by_id(admin_page, env, course_b["course_id"], use_global_domain=True)
            totals_b = page_b.read_map_totals()
            assert totals_b["Слушателей"]["value"] == "2", (
                "После перехода на курс B карта должна показывать его собственные "
                "данные, а не оставшиеся данные курса A"
            )
