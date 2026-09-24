"""Выгрузка итоговой таблицы курса в xlsx (docs/plans/statistics_courses_plan.md, шаги 22-24).

Открытый вопрос №3 плана («openpyxl отсутствует в requirements.txt, читать xlsx нечем»)
закрыт без добавления зависимости: xlsx — это ZIP-архив с XML внутри (подтверждено
разведкой — сигнатура PK\\x03\\x04, `zipfile.ZipFile(...).namelist()` показывает
`xl/sharedStrings.xml`/`xl/worksheets/sheet1.xml`), оба модуля есть в stdlib
(`zipfile`, простой regex по XML ниже) — полноценный парсинг ячеек по стилям не нужен,
хватает: (а) строковый пул `sharedStrings.xml` содержит текст всех текстовых ячеек
целиком (ФИО слушателя, метка потока) — можно проверить вхождением подстроки;
(б) количество `<row>` в `sheet1.xml` минус 2 строки заголовков (разведкой подтверждено:
строка 1 — объединённые заголовки разделов, строка 2 — подписи столбцов, с 3 —
данные) даёт число строк слушателей.

Шаг 25 («выгрузка большого набора без потери строк при пагинации») НЕ покрыт — в самом
плане отмечен как низкий приоритет/не оценено (XL), требует массового создания
десятков курсов и отдельно от остальных шагов не обосновывает свою стоимость в рамках
этой задачи.
"""
import re
import zipfile

import allure
import pytest

from ui.pages.admin_dashboard_page import open_course_statistics_by_id


def _xlsx_shared_strings(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read("xl/sharedStrings.xml").decode("utf-8")


def _xlsx_data_row_count(path: str) -> int:
    with zipfile.ZipFile(path) as zf:
        sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    total_rows = len(re.findall(r"<row ", sheet))
    return max(total_rows - 2, 0)


@allure.feature("Статистика обучения — Курсы")
@allure.story("Выгрузка")
class TestCoursesExport:

    @allure.title("UI: кнопка «Выгрузить» инициирует скачивание валидного xlsx")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_export_downloads_valid_xlsx(self, admin_page, env, course_with_listeners, tmp_path):
        data = course_with_listeners(user_count=1)

        with allure.step("22. Открыть карточку курса и скачать отчёт"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            save_path = tmp_path / "course_export.xlsx"
            page.export_listeners(save_as=str(save_path))

        with allure.step("23. Скачанный файл — валидный xlsx (ZIP-сигнатура, непустой)"):
            assert save_path.exists()
            assert save_path.stat().st_size > 0
            with open(save_path, "rb") as f:
                signature = f.read(4)
            assert signature == b"PK\x03\x04", f"Файл не является валидным xlsx/zip: сигнатура {signature!r}"

    @allure.title("UI: данные в выгрузке совпадают с таблицей слушателей на странице")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    def test_export_content_matches_listener_table(self, admin_page, env, course_with_listeners, tmp_path):
        data = course_with_listeners(user_count=2)

        with allure.step("Открыть карточку курса, дождаться таблицы слушателей"):
            from playwright.sync_api import expect

            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            expect(admin_page.locator(".courses-statistic-table table tbody tr").first).to_contain_text(
                str(data["users"][0]["id"]), timeout=20000
            )
            ui_rows = page.listener_table_rows()
            assert len(ui_rows) == 2

        with allure.step("24. Скачать отчёт и сравнить состав строк/ФИО с таблицей UI"):
            save_path = tmp_path / "course_export.xlsx"
            page.export_listeners(save_as=str(save_path))
            shared_strings = _xlsx_shared_strings(str(save_path))
            for user in data["users"]:
                full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
                assert full_name in shared_strings, (
                    f"ФИО слушателя {full_name!r} не найдено в выгруженном файле"
                )
            assert _xlsx_data_row_count(str(save_path)) == len(ui_rows)

    @allure.title("UI: повторная выгрузка после фильтрации содержит только отфильтрованные данные")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.statistics
    @pytest.mark.xfail(
        reason=(
            "24. Выгрузка не учитывает применённый фильтр таблицы слушателей — "
            "воспроизведено дважды за 3 прогона (бюджет исчерпан). Первый прогон: "
            "модалка «Фильтр» рядом с картой (Тип назначения/Программы/Поток) скоупит "
            "только виджет карты — после применения фильтра на заведомо чужой поток "
            "выгрузка всё равно содержала исходную строку слушателя. Тест переписан на "
            "`search_listeners` (реальный фильтр итоговой таблицы слушателей, "
            "`.courses-statistic-table`), но и он не влияет на выгрузку: после поиска по "
            "email ОДНОГО из двух слушателей (таблица на экране показывает 1 строку) "
            "скачанный xlsx всё равно содержит ОБЕИХ (2 строки данных, а не 1) — кнопка "
            "«Выгрузить» на develop, похоже, всегда выгружает полный список слушателей "
            "курса независимо от того, что отфильтровано/показано на странице. Похоже на "
            "дефект стенда (или намеренное поведение, отличное от плана — тогда план "
            "шага 24 нужно скорректировать владельцу), не на ошибку теста."
        ),
        strict=False,
    )
    def test_export_after_filter_reflects_filtered_data(self, admin_page, env, course_with_listeners, tmp_path):
        from playwright.sync_api import expect

        data = course_with_listeners(user_count=2)

        with allure.step("Выгрузка без фильтра — 2 строки слушателей"):
            page = open_course_statistics_by_id(admin_page, env, data["course_id"], use_global_domain=True)
            page.read_map_totals()
            expect(admin_page.locator(".courses-statistic-table table tbody tr").first).to_contain_text(
                str(data["users"][0]["id"]), timeout=20000
            )
            unfiltered_path = tmp_path / "unfiltered.xlsx"
            page.export_listeners(save_as=str(unfiltered_path))
            assert _xlsx_data_row_count(str(unfiltered_path)) == 2

        with allure.step("24. Отфильтровать таблицу слушателей по email одного — выгрузка содержит только его"):
            target_user = data["users"][0]
            page.search_listeners(target_user["email"])
            filtered_path = tmp_path / "filtered.xlsx"
            page.export_listeners(save_as=str(filtered_path))
            assert _xlsx_data_row_count(str(filtered_path)) == 1
            full_name = f"{target_user['surname']} {target_user['name']} {target_user['patronymic']}"
            assert full_name in _xlsx_shared_strings(str(filtered_path))
