"""Админка: дашборды статистики программ и курсов (/admin/learning-statistics/*).

Перенос локаторов src/ui/pages/dashboard_page.py коллеги (отдельная история
origin/feature/dashboard-autotests, код взят через `git show`, ветка не сливалась)
в наш Page Object.
"""
import re

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class AdminDashboardPage(BasePage):
    PROGRAMS_PATH = "/admin/learning-statistics/programs"
    COURSES_PATH = "/admin/learning-statistics/courses"

    def __init__(self, page: Page):
        super().__init__(page)

    def open_programs_dashboard(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.PROGRAMS_PATH}")
        expect(self.page).to_have_url(
            re.compile(r".*/admin/learning-statistics/programs.*"), timeout=30000
        )

    def open_courses_dashboard(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url.rstrip('/')}{self.COURSES_PATH}")
        expect(self.page).to_have_url(
            re.compile(r".*/admin/learning-statistics/courses.*"), timeout=30000
        )

    def search(self, name: str) -> None:
        search_input = self.page.locator("input[data-qa='km-search']").or_(
            self.page.locator("input[placeholder='Поиск']")
        )
        expect(search_input.first).to_be_visible(timeout=15000)
        search_input.first.fill(name, timeout=5000)
        search_input.first.press("Enter")

    def row(self, entity_name: str) -> Locator:
        safe = entity_name.replace("'", "")
        return self.page.locator(
            f"xpath=//tr[.//a[normalize-space()='{safe}'] or .//*[normalize-space()='{safe}']]"
        )

    def row_cell(self, row: Locator, cell_index: int) -> Locator:
        return row.locator(f"xpath=.//td[{cell_index}]")

    def find_row(self, entity_name: str) -> Locator:
        """Найти строку сущности по имени: поиск + ожидание появления строки в таблице."""
        self.search(entity_name)
        row = self.row(entity_name)
        expect(row).to_be_visible(timeout=30000)
        return row

    def assert_program_row(
        self,
        program_name: str,
        *,
        schedule_items_completeness: int = None,
        assignments_count: int = None,
        assignments_new: int = None,
        assignments_in_progress: int = None,
        assignments_passed: int = None,
    ) -> None:
        """Проверить значения ячеек строки программы. Столбцы совпадают с
        /admin/learning-statistics/programs: 6 — завершённость мероприятий,
        7 — всего назначений, 8 — новых, 9 — в процессе, 10 — пройдено."""
        row = self.find_row(program_name)
        checks = {
            6: schedule_items_completeness,
            7: assignments_count,
            8: assignments_new,
            9: assignments_in_progress,
            10: assignments_passed,
        }
        for cell_index, value in checks.items():
            if value is not None:
                expect(self.row_cell(row, cell_index)).to_contain_text(str(value), timeout=15000)

    def assert_course_row(
        self,
        course_name: str,
        *,
        passed_percentage: int = None,
        total: int = None,
        not_started: int = None,
        in_progress: int = None,
        passed: int = None,
    ) -> None:
        """Проверить значения ячеек строки курса. Столбцы совпадают с
        /admin/learning-statistics/courses: 5 — % пройденных, 6 — всего,
        7 — не начато, 8 — в процессе, 9 — пройдено."""
        row = self.find_row(course_name)
        checks = {
            5: f"{passed_percentage}%" if passed_percentage is not None else None,
            6: total,
            7: not_started,
            8: in_progress,
            9: passed,
        }
        for cell_index, value in checks.items():
            if value is not None:
                expect(self.row_cell(row, cell_index)).to_contain_text(str(value), timeout=15000)

    def open_course_statistics(self, course_name: str) -> "AdminCourseStatisticsPage":
        """Перейти из строки таблицы курсов в карточку статистики курса (клик по ссылке
        названия курса открывает /admin/learning-statistics/courses/{id}/info на той же
        вкладке — отдельного окна/таба не открывается)."""
        row = self.find_row(course_name)
        row.locator("a.vs-table__link").first.click()
        expect(self.page).to_have_url(
            re.compile(r".*/admin/learning-statistics/courses/\d+/info.*"), timeout=30000
        )
        return AdminCourseStatisticsPage(self.page)


class AdminCourseStatisticsPage(BasePage):
    """Карточка курса в статистике обучения (/admin/learning-statistics/courses/{id}/info,
    вкладка «Инфо» по умолчанию — вкладку «Оценки и отзывы» этот класс не покрывает).

    Устройство страницы (проверено вручную на develop, HEADLESS=1, курс id=27 —
    "course-scorm 2026-06-26 14:26:24" — и на курсах, поднятых через
    created_schedule_item/created_tincan/created_user):

    - «Интерактивная карта»: SVG с регионами РФ (`svg.vs-interactive-map`), каждый регион —
      `<path data-region-id="000000NNN" data-region-name="...">`. Выбранный регион получает
      доп. класс `vs-interactive-map__region_selected` — проверка выделения идёт по этому
      DOM-классу, а не по пикселям/скриншотам (см. docs/plans/statistics_courses_plan.md,
      раздел «Не автоматизируем и почему»).
    - Панель `.map-dashboard__info` с вкладками (`.map-dashboard__info-tab`, role=tab):
      пока НЕ выбран ни один регион — единственная вкладка «Всего» с абсолютными числами;
      как только выбран хотя бы один регион — вкладка «Всего» пропадает, вместо неё
      появляются «Графики» (те же 4 круговых диаграммы, но с процентом от общего количества
      слушателей курса) и «Таблица» (построчно по каждому выбранному региону).
    - Круговые диаграммы (`.map-dashboard__chart-block` × 4: Слушателей/Завершили курс/
      Проходят курс/Назначено) рисуются в `<canvas>` — значение оттуда через DOM не достать,
      но подписи `.map-dashboard__chart-label` ("Слушателей: 11") и `.map-dashboard__chart-percent`
      ("9.09%", видим только при выбранном регионе) дублируют те же числа текстом.
    - Фильтр карты (кнопка `.dashboard-filters__btn` рядом с "Интерактивная карта") — модалка
      с полем "Тип назначения" (мультиселект: Инд.трек / Программы / База знаний), которое
      включает/выключает поля "Программы" (single-select) и "Поток" (мультиселект) — оба
      задизейблены, пока в "Тип назначения" не выбрано "Программы"; при выборе "Программы"
      поле "Поток" становится обязательным (валидация "Поле обязательно для заполнения" не
      даёт закрыть модалку кнопкой "Применить", пока поток не выбран). Оба select — Vuetify
      autocomplete с подгрузкой по подстроке: чтобы найти свежесозданную программу/поток,
      после открытия списка нужно НАБРАТЬ текст на клавиатуре (page.keyboard.type), а не просто
      проскроллить статичный список — иначе только что созданная программа не попадёт в
      показанные ~20 вариантов.
    - Итоговая таблица слушателей (`.courses-statistic-table`) реально содержит 8 столбцов:
      ID, ФИО, Email, Статус курса, Тип назначения, Дата начала обучения по курсу, Дата
      завершения обучения по курсу, Время прохождения мин. Столбцов "Текущий раздел" и
      "Прогресс" в вёрстке НЕТ, хотя API `/statistics/courses/{id}/users` отдаёт похожие поля
      current_child/passed_percent — бэкенд их вычисляет, но в таблицу не выводит. Так же нет
      отдельного столбца "Дата завершения последнего пройденного раздела" — есть только "Дата
      завершения обучения по курсу" (общее завершение курса, а не раздела). Это несовпадение
      с формулировками ПМИ из docs/plans/statistics_courses_plan.md стоит сверить с владельцем
      перед тем, как писать проверки конкретных столбцов (см. также открытый вопрос "состав
      столбцов требует ручной сверки с ДТТ" в плане).
    - Кнопка "Выгрузить" НЕ скачивает файл сразу: она запускает генерацию отчёта на бэкенде,
      после чего рядом с кнопкой появляется ссылка `a:has-text('Скачать отчет')` на
      `/static/tmp/{uuid}/course_users_statistic_{date}_{ts}.xlsx` — только клик по этой
      ссылке инициирует реальную загрузку (подтверждено `page.expect_download`, файл проходит
      как валидный xlsx — сигнатура ZIP `PK\x03\x04`).

    Открытый вопрос плана "как регион слушателя связан с регионом на карте" —
    ЗАКРЫТ разведкой (API `/statistics/courses/{id}/map`, повторные прогоны с разными
    комбинациями входных данных): регион на карте НЕ определяется ни `region_id`/
    `municipality_id` пользователя (generate_user_payload), ни регионом
    модуля/элемента расписания (generate_module_payload/generate_schedule_item_payload,
    несмотря на то что оба по умолчанию используют region_name="Москва" — совпадение,
    сбившее с толку на первых прогонах). Во всех контролируемых прогонах (region_id
    пользователя 1 и 9, регион модуля явно выставлен в "Костромская область" через
    modules_endpoint.update) карта стабильно показывала "Москва" — то есть в этом
    окружении реальный источник региональной привязки слушателя для карты курса
    остаётся не найден (возможно, geo-IP при первом входе слушателя, тенантный
    дефолт или иной, не проверенный здесь атрибут). Для тестов, которым нужен
    конкретный регион с данными, единственный надёжный способ — прочитать
    `DashboardsEndpoint.get_course_map` и использовать регион(ы), где `total_count > 0`,
    а не подбирать region_id заранее.
    """

    def __init__(self, page: Page):
        super().__init__(page)

    TYPE_INDIVIDUAL = "Инд.трек"
    TYPE_PROGRAMS = "Программы"
    TYPE_KNOWLEDGE_BASE = "База знаний"

    # ---- Карта ----

    def region(self, *, name: str = None, code: str = None) -> Locator:
        """Локатор региона на карте по названию (data-region-name) или коду
        (data-region-id, 9-значный код с ведущими нулями — тот же формат, что
        `region_code` в ответе DashboardsEndpoint.get_course_map)."""
        if code:
            return self.page.locator(f"svg.vs-interactive-map path[data-region-id='{code}']")
        return self.page.locator(f"svg.vs-interactive-map path[data-region-name='{name}']")

    def is_region_selected(self, *, name: str = None, code: str = None) -> bool:
        classes = self.region(name=name, code=code).get_attribute("class") or ""
        return "vs-interactive-map__region_selected" in classes

    def toggle_region(self, *, name: str = None, code: str = None) -> None:
        """Выбрать/снять выбор региона на карте (повторный вызов на том же регионе —
        снятие выбора). Клик по обычному Locator.click() у мелких/дальних регионов на
        develop часто зависает в бесконечном ретрае actionability-проверки (соседний
        регион/тулбар перехватывает точку клика на SVG-путях с крошечным bounding box) —
        поэтому кликаем через dispatch_event('click'), в обход хит-теста Playwright."""
        self.region(name=name, code=code).dispatch_event("click")

    def selected_region_names(self) -> list:
        """Названия всех выбранных регионов (в порядке, в котором они лежат в SVG,
        не обязательно в порядке кликов)."""
        return self.page.locator(
            "svg.vs-interactive-map path.vs-interactive-map__region_selected"
        ).evaluate_all("els => els.map(e => e.getAttribute('data-region-name'))")

    def map_tab_names(self) -> list:
        """Названия вкладок над круговыми диаграммами: ["ВСЕГО"] когда не выбран ни один
        регион, ["ГРАФИКИ", "ТАБЛИЦА"] — когда выбран хотя бы один. Регистр — ЗАГЛАВНЫЙ:
        вёрстка задаёт "Всего"/"Графики"/"Таблица", но CSS text-transform: uppercase
        меняет то, что реально возвращает Locator.inner_text() (сравнивайте с константами
        TYPE_*/строками в верхнем регистре, а не с исходным текстом из вёрстки)."""
        return [t.strip() for t in self.page.locator(".map-dashboard__info-tab").all_inner_texts()]

    def open_map_tab(self, tab_name: str) -> None:
        tab = self.page.locator(".map-dashboard__info-tab").filter(has_text=tab_name).first
        expect(tab).to_be_visible(timeout=10000)
        tab.click()

    def read_map_totals(self) -> dict:
        """Прочитать 4 круговые диаграммы карты (подписи рядом с canvas, само число
        в canvas через DOM не читается). Формат: {"Слушателей": {"value": "11",
        "percent": None}, ...}; percent заполнен, только если выбран регион (вкладка
        «Графики») — на вкладке «Всего» это поле всегда None.

        Данные виджета карты приходят отдельным XHR (`/statistics/courses/{id}/map`)
        после того, как открылась сама страница, и на develop подтверждена та же
        асинхронность статистики, что и у остальных дашбордов (см.
        DashboardsEndpoint.wait_for_course_row) — сразу после навигации подписи
        какое-то время пустые ("Слушателей:", без числа). page.wait_for_load_state
        ("networkidle") для этого не подходит: на странице держится открытый websocket
        (wss://.../connection/websocket), из-за которого networkidle может не
        наступить вообще. Поэтому ждём появления цифры в первой подписи через
        обычный web-first expect() с увеличенным таймаутом."""
        first_label = self.page.locator(".map-dashboard__chart-block").first.locator(
            ".map-dashboard__chart-label"
        )
        expect(first_label).to_contain_text(re.compile(r"\d"), timeout=30000)

        result = {}
        blocks = self.page.locator(".map-dashboard__chart-block")
        for i in range(blocks.count()):
            block = blocks.nth(i)
            label_text = block.locator(".map-dashboard__chart-label").inner_text()
            name, _, value = label_text.partition(":")
            percent_locator = block.locator(".map-dashboard__chart-percent")
            percent = percent_locator.inner_text().strip() if percent_locator.is_visible() else None
            result[name.strip()] = {"value": value.strip(), "percent": percent or None}
        return result

    def read_region_table_rows(self) -> list:
        """Строки вкладки «Таблица» (доступна только когда выбран ≥1 регион) — по одной
        строке на выбранный регион, столбцы: Регион, Слушателей, Завершили курс,
        Проходят курс, Назначено. Порядок строк на develop совпадает с порядком выбора,
        визуально алфавитный, только если сортировать значения перед сравнением."""
        table = self.page.locator(".map-dashboard__table table")
        headers = [h.strip() for h in table.locator("thead th").all_inner_texts()]
        rows = []
        for row in table.locator("tbody tr").all():
            cells = [c.strip() for c in row.locator("td").all_inner_texts()]
            rows.append(dict(zip(headers, cells)))
        return rows

    # ---- Фильтр карты ----

    def open_map_filter(self) -> Locator:
        self.page.locator(".map-dashboard .dashboard-filters__btn").click()
        dialog = self.page.locator(".v-dialog--active")
        expect(dialog).to_be_visible(timeout=10000)
        return dialog

    def _choose_in_filter(self, dialog: Locator, prepared_key: str, *values: str, search: bool = False) -> None:
        """Открыть select фильтра (по атрибуту preparedkey — кликать нужно по
        обёртке .v-input, не по внутреннему <input>: у него нулевой размер и
        Playwright падает с "outside of viewport") и выбрать значение(я).

        search=True — набрать текст перед выбором: оба select'а — Vuetify autocomplete
        с подгрузкой по подстроке, без набора текста в списке видно только первые ~20
        вариантов и свежесозданная программа/поток может туда не попасть.

        Закрываем открывшееся меню кликом по заголовку модалки, а не Escape: Escape для
        мультиселекта с чипами («Тип назначения», «Поток») закрывает не меню, а весь
        диалог целиком (потеряется весь прогресс заполнения формы)."""
        field = dialog.locator(f".v-input[preparedkey='{prepared_key}']")
        field.click()
        menu = self.page.locator(".v-menu__content.menuable__content__active")
        expect(menu).to_be_visible(timeout=10000)
        for value in values:
            if search:
                self.page.keyboard.type(value)
                self.page.wait_for_timeout(700)
            menu.locator(".v-list-item").filter(has_text=value).first.click(timeout=10000)
        dialog.locator(".base-modal__header").click()

    def set_assignment_types(self, dialog: Locator, *types: str) -> None:
        """types — любая комбинация TYPE_INDIVIDUAL/TYPE_PROGRAMS/TYPE_KNOWLEDGE_BASE.
        Выбор TYPE_PROGRAMS включает поля "Программы"/"Поток" (см. is_program_field_enabled/
        is_stream_field_enabled) и делает "Поток" обязательным для кнопки "Применить"."""
        self._choose_in_filter(dialog, "type", *types)

    def is_program_field_enabled(self, dialog: Locator) -> bool:
        classes = dialog.locator(".v-input[preparedkey='program']").get_attribute("class") or ""
        return "v-input--is-disabled" not in classes

    def is_stream_field_enabled(self, dialog: Locator) -> bool:
        classes = dialog.locator(".v-input[preparedkey='stream_id']").get_attribute("class") or ""
        return "v-input--is-disabled" not in classes

    def select_program(self, dialog: Locator, program_name: str) -> None:
        self._choose_in_filter(dialog, "program", program_name, search=True)

    def select_stream(self, dialog: Locator, stream_name: str) -> None:
        self._choose_in_filter(dialog, "stream_id", stream_name, search=True)

    def apply_filter(self, dialog: Locator) -> None:
        dialog.locator("button:has-text('Применить')").click()
        expect(dialog).to_be_hidden(timeout=15000)

    def reset_filter(self, dialog: Locator) -> None:
        dialog.locator("button:has-text('Очистить')").click()

    # ---- Итоговая таблица слушателей ----

    def search_listeners(self, text: str) -> None:
        """Поиск по итоговой таблице слушателей. Инпут поиска НЕ вложен в
        `.courses-statistic-table` (это класс только самой таблицы) — он в соседнем
        тулбаре `.vs-table-top-bar__search` перед ней, поэтому ищем без этого скоупа;
        на карточке курса такой инпут единственный (у таблицы регионов на вкладке
        «Таблица» своего поиска нет)."""
        search_input = self.page.locator("input[data-qa='km-search']")
        expect(search_input).to_be_visible(timeout=15000)
        search_input.fill(text)
        search_input.press("Enter")

    def listener_table_columns(self) -> list:
        table = self.page.locator(".courses-statistic-table table")
        return [h.strip() for h in table.locator("thead th").all_inner_texts()]

    def listener_table_rows(self) -> list:
        """Строки итоговой таблицы слушателей как список dict {заголовок: значение} —
        общий метод по факту реального состава столбцов (см. докстринг класса)."""
        table = self.page.locator(".courses-statistic-table table")
        headers = self.listener_table_columns()
        rows = []
        for row in table.locator("tbody tr").all():
            cells = [c.strip() for c in row.locator("td").all_inner_texts()]
            rows.append(dict(zip(headers, cells)))
        return rows

    def export_listeners(self, save_as: str = None):
        """Клик "Выгрузить" → дождаться ссылки "Скачать отчет" (бэкенд генерирует xlsx не
        мгновенно) → клик по ссылке инициирует реальную загрузку. Возвращает Playwright
        Download; save_as — опционально сохранить файл по указанному пути."""
        self.page.locator("button:has-text('Выгрузить')").click()
        link = self.page.locator("a:has-text('Скачать отчет')")
        expect(link).to_be_visible(timeout=30000)
        with self.page.expect_download(timeout=30000) as download_info:
            link.click()
        download = download_info.value
        if save_as:
            download.save_as(save_as)
        return download
