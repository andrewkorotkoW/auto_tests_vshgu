"""Фикстуры для тестов дашбордов статистики (/admin/learning-statistics/*).

Данные для дашбордов готовятся через наши фикстуры/эндпоинты (created_schedule_item,
created_tincan, created_user, assignments_endpoint, modules_endpoint,
schedule_items_endpoint) — без переноса JSON-подготовки из
tests/api/helpers/dashboard_prepare_api.py коллеги (origin/feature/dashboard-autotests,
отдельная история, код туда не сливался).

Сам тест дашборда сюда не входит — это отдельная задача, использующая эти фикстуры
и ui.pages.admin_dashboard_page.AdminDashboardPage.
"""
import allure
import pytest

from api.endpoints.assignments import CONTENT_STATE_PASSED
from ui.pages.user_sidebar_page import UserSidebarPage


@pytest.fixture
def dashboards_admin_page(admin_page, env):
    """Страница админки, открытая на разделе дашбордов статистики."""
    admin_page.goto(f"{env.ui_base_url}/admin/learning-statistics")
    # storage_state логинит без формы, поэтому онбординг-тур/плашка техработ ещё
    # не пройдены — закрываем, иначе затемнение перехватывает клики.
    UserSidebarPage(admin_page).dismiss_popups()
    yield admin_page


@pytest.fixture
def dashboard_data(
    created_schedule_item,
    created_tincan,
    created_user,
    programs_endpoint,
    modules_endpoint,
    assignments_endpoint,
    schedule_items_endpoint,
    dashboards_endpoint,
):
    """Готовит программу → поток → модуль → очное мероприятие с дистанционным
    курсом в модуле и двумя назначенными слушателями: первому — курс отмечен
    пройденным и он зарегистрирован на очное мероприятие (данные для строк
    дашбордов программ и курсов)."""
    with allure.step("Подготовить программу → поток → модуль → очное мероприятие"):
        schedule_item = created_schedule_item()
        program_id = schedule_item["program_id"]
        stream_id = schedule_item["stream_id"]
        module_id = schedule_item["module_id"]
        program_name = programs_endpoint.get(program_id)["attributes"]["name"]

    with allure.step("Добавить дистанционный курс в модуль"):
        course = created_tincan()
        assignments_endpoint.assign_content_to_module(
            program_id, stream_id, module_id, [course["id"]]
        )
        stream_content_id = modules_endpoint.find_stream_content_id(
            program_id, stream_id, module_id, course["id"]
        )

    with allure.step("Назначить слушателей на поток"):
        users = [created_user() for _ in range(2)]
        user_ids = [user["id"] for user in users]
        assignments_endpoint.assign(program_id, stream_id, user_ids)

    with allure.step("Первому слушателю: пройденный курс + регистрация на мероприятие"):
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
        schedule_items_endpoint.register_user(schedule_item["id"], first_user_id)

    with allure.step("Дождаться появления строк в статистике дашбордов"):
        # Статистика считается асинхронно бэкендом после назначений/смены статусов —
        # сразу после запросов выше строк в /statistics/* может ещё не быть.
        # Ждём не только появления строки, но и финальных значений: завершённость
        # мероприятий (регистрация на schedule item) и число назначений считаются
        # отдельными пересчётами и на develop отстают на десятки секунд — UI-тест
        # падал на «0 вместо 1» в колонке завершённости (07.10).
        dashboards_endpoint.wait_for_program_row(
            program_name,
            predicate=lambda row: int(row.get("completeness_schedule_items") or 0) >= 1
            and int(row.get("assignments_count") or 0) >= len(user_ids),
            timeout=90,
        )
        dashboards_endpoint.wait_for_course_row(course["name"], stream_id)

    return {
        "program_id": program_id,
        "program_name": program_name,
        "stream_id": stream_id,
        "module_id": module_id,
        "schedule_item_id": schedule_item["id"],
        "course_id": course["id"],
        "course_name": course["name"],
        "stream_content_id": stream_content_id,
        "users": users,
    }
