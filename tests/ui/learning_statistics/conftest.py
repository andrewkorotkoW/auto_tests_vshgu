"""Фикстуры для карточки статистики курса (/admin/learning-statistics/courses/{id}/info).

Отдельно от tests/ui/dashboards/conftest.py: тот каталог покрывает СПИСКИ
/admin/learning-statistics/programs и /courses (ui.pages.admin_dashboard_page.AdminDashboardPage),
этот — детальную КАРТОЧКУ конкретного курса (карта регионов, фильтр, итоговая таблица
слушателей, выгрузка — ui.pages.admin_dashboard_page.AdminCourseStatisticsPage), см.
docs/plans/statistics_courses_plan.md.
"""
import allure
import pytest

from api.endpoints.assignments import CONTENT_STATE_PASSED
from ui.pages.admin_dashboard_page import AdminDashboardPage
from ui.pages.login_page import LoginPage
from ui.pages.tincan_page import TincanPage
from ui.pages.user_sidebar_page import UserSidebarPage


@pytest.fixture
def course_statistics_admin_page(admin_page, env):
    """Страница администратора со списком /admin/learning-statistics/courses, готовая
    к AdminDashboardPage.open_course_statistics(...)."""
    dashboard_page = AdminDashboardPage(admin_page)
    dashboard_page.open_courses_dashboard(env.ui_base_url)
    # storage_state логинит без формы — онбординг-тур/плашка техработ ещё не пройдены
    # и перехватывают клики по строкам таблицы, если их не закрыть.
    UserSidebarPage(admin_page).dismiss_popups()
    yield dashboard_page


@pytest.fixture
def course_statistics_data(
    created_schedule_item,
    created_tincan,
    created_user,
    programs_endpoint,
    streams_endpoint,
    modules_endpoint,
    assignments_endpoint,
    dashboards_endpoint,
):
    """Готовит программу → поток → модуль → дистанционный курс с двумя назначенными
    слушателями — данные для карты/фильтра/итоговой таблицы карточки курса. Первому
    слушателю курс отмечен пройденным через API (assignments_endpoint.change_state),
    чтобы столбец "Статус курса"/диаграмма "Завершили курс" были не нулевыми у части
    выборки, а не только "Назначено" у всех.

    Какой регион карты получит слушателей — заранее НЕ определено и не гарантируется
    (см. открытый вопрос в докстринге AdminCourseStatisticsPage: ни region_id/
    municipality_id пользователя, ни регион модуля/элемента расписания не оказались
    надёжным предиктором на develop). Тесты, которым нужен конкретный регион с
    данными, должны прочитать его из DashboardsEndpoint.get_course_map(course_id)
    после этой фикстуры (регион(ы) с total_count > 0), а не полагаться на то, что
    это будет какой-то конкретный регион.
    """
    with allure.step("Подготовить программу → поток → модуль"):
        schedule_item = created_schedule_item()
        program_id = schedule_item["program_id"]
        stream_id = schedule_item["stream_id"]
        module_id = schedule_item["module_id"]
        program_name = programs_endpoint.get(program_id)["attributes"]["name"]
        stream_name = streams_endpoint.get(program_id, stream_id)["attributes"]["name"]

    with allure.step("Добавить дистанционный курс в модуль"):
        course = created_tincan()
        assignments_endpoint.assign_content_to_module(
            program_id, stream_id, module_id, [course["id"]]
        )
        stream_content_id = modules_endpoint.find_stream_content_id(
            program_id, stream_id, module_id, course["id"]
        )

    with allure.step("Назначить двух слушателей на поток"):
        users = [created_user() for _ in range(2)]
        user_ids = [user["id"] for user in users]
        assignments_endpoint.assign(program_id, stream_id, user_ids)

    with allure.step("Первому слушателю: курс отмечен пройденным"):
        stream_assignments = assignments_endpoint.list_for_stream(
            program_id, stream_id, [stream_content_id]
        )
        assignment_by_user_id = {
            int(item["user_id"]): int(item["assignment_id"])
            for item in stream_assignments
        }
        first_user_id = user_ids[0]
        assignments_endpoint.change_state(
            user_id=first_user_id,
            assignment_id=assignment_by_user_id[first_user_id],
            stream_content_id=stream_content_id,
            state=CONTENT_STATE_PASSED,
        )

    with allure.step("Дождаться появления строки курса в статистике"):
        # Статистика считается асинхронно — сразу после назначений/смены статуса
        # строки в /statistics/courses/* может ещё не быть (см. DashboardsEndpoint).
        dashboards_endpoint.wait_for_course_row(course["name"], stream_id)

    return {
        "program_id": program_id,
        "program_name": program_name,
        "stream_id": stream_id,
        "stream_name": stream_name,
        "module_id": module_id,
        "course_id": course["id"],
        "course_name": course["name"],
        "stream_content_id": stream_content_id,
        "users": users,
        "passed_user_id": user_ids[0],
        "not_started_user_id": user_ids[1],
    }


@pytest.fixture
def listener_passes_course_ui():
    """Фабрика: слушатель логинится и открывает дистанционный курс в отдельном
    браузерном контексте (page слушателя должен быть создан тестом отдельно от
    admin_page, напр. через фикстуру `page` или свой browser.new_context) — нужно
    для шагов плана 19-21 ("в процессе"/"пройдено"/"время прохождения" в карточке
    курса должны отражать реальное прохождение, а не имитацию через
    assignments_endpoint.change_state).

    ИЗВЕСТНЫЙ ДЕФЕКТ СТЕНДА (develop), тот же класс, что задокументирован как xfail в
    tests/ui/courses/tincan/stream/test_user_tincan_flow.py: карточка программы
    показывает вкладки «Расписание» / «Курсы и тесты» / «Игровая сессия» неактивными,
    пока строка модуля не развёрнута вручную (шеврон справа от даты модуля) — точный
    локатор шеврона не подтверждён. TincanPage.start_tincan ищет карточку курса по
    тексту сразу, без разворачивания модуля, и виснет на ожидании видимости.

    Эта фикстура НЕ обходит дефект молча (не эмулирует прохождение через API вместо
    UI) — она вызывает TincanPage.start_tincan как есть, чтобы тест, использующий её
    для шагов 19-21, ловил тот же xfail, а не тихо терял часть проверки. Когда дефект
    на стенде будет исправлен (или найдётся рабочий локатор шеврона), фикстура и тесты
    на ней заработают без изменений.
    """

    def _pass(page, user: dict, program_name: str) -> TincanPage:
        login_page = LoginPage(page)
        login_page.login(user["email"], user["password"])
        UserSidebarPage(page).dismiss_popups()

        tincan_page = TincanPage(page)
        tincan_page.start_tincan(program_name)
        return tincan_page

    return _pass
