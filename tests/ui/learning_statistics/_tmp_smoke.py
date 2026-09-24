import allure
import openpyxl
import pytest

from ui.pages.admin_dashboard_page import AdminCourseStatisticsPage


@allure.feature("smoke")
@pytest.mark.ui
@pytest.mark.statistics
def test_smoke_course_statistics_page(course_statistics_admin_page, course_statistics_data, env):
    course_page = course_statistics_admin_page.open_course_statistics(
        course_statistics_data["course_name"]
    )
    assert isinstance(course_page, AdminCourseStatisticsPage)

    # --- карта: без выбора региона только "Всего" ---
    assert course_page.map_tab_names() == ["ВСЕГО"]
    totals = course_page.read_map_totals()
    print("TOTALS:", totals)
    assert totals["Слушателей"]["value"] == "2"

    print("map tabs (no selection):", course_page.map_tab_names())


@pytest.mark.ui
@pytest.mark.statistics
def test_smoke_filter_and_export(course_statistics_admin_page, course_statistics_data, dashboards_endpoint, env, tmp_path):
    course_id = course_statistics_data["course_id"]
    course_page = course_statistics_admin_page.open_course_statistics(
        course_statistics_data["course_name"]
    )

    # --- карта: найти регион(ы) с данными через API и выбрать/снять на карте ---
    map_data = dashboards_endpoint.get_course_map(course_id)
    nonzero = [r for r in map_data if r["data"]["total_count"] > 0]
    print("NONZERO REGIONS:", nonzero)
    assert nonzero, "Ожидали хотя бы один регион с данными"
    region_code = nonzero[0]["region"]["region_code"]
    region_name = nonzero[0]["region"]["region_name"]

    assert course_page.is_region_selected(code=region_code) is False
    course_page.toggle_region(code=region_code)
    assert course_page.is_region_selected(code=region_code) is True
    assert set(course_page.map_tab_names()) == {"ГРАФИКИ", "ТАБЛИЦА"}
    assert region_name in course_page.selected_region_names()

    course_page.open_map_tab("Таблица")
    rows = course_page.read_region_table_rows()
    print("REGION TABLE ROWS:", rows)
    assert any(r["Регион"] == region_name for r in rows)

    course_page.toggle_region(code=region_code)
    assert course_page.is_region_selected(code=region_code) is False
    assert course_page.map_tab_names() == ["ВСЕГО"]

    # --- фильтр карты ---
    dialog = course_page.open_map_filter()
    assert course_page.is_program_field_enabled(dialog) is False
    course_page.set_assignment_types(dialog, course_page.TYPE_PROGRAMS)
    assert course_page.is_program_field_enabled(dialog) is True
    course_page.select_program(dialog, course_statistics_data["program_name"])
    assert course_page.is_stream_field_enabled(dialog) is True
    course_page.select_stream(dialog, course_statistics_data["stream_name"])
    course_page.apply_filter(dialog)
    print("FILTER APPLIED OK")

    # --- итоговая таблица слушателей ---
    columns = course_page.listener_table_columns()
    print("LISTENER TABLE COLUMNS:", columns)
    assert "ID" in columns and "ФИО" in columns and "Статус курса" in columns
    rows = course_page.listener_table_rows()
    print("LISTENER TABLE ROWS:", rows)
    assert len(rows) == 2

    course_page.search_listeners(course_statistics_data["users"][0]["email"])
    filtered_rows = course_page.listener_table_rows()
    print("FILTERED ROWS:", filtered_rows)
    assert len(filtered_rows) == 1

    # --- выгрузка ---
    save_path = tmp_path / "export.xlsx"
    course_page.export_listeners(save_as=str(save_path))
    wb = openpyxl.load_workbook(str(save_path))
    ws = wb.active
    print("XLSX FIRST ROW:", [c.value for c in next(ws.iter_rows())])
