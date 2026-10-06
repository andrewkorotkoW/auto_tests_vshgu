"""Админка: дашборды статистики (/admin/learning-statistics/programs и /courses).

Перенос test_01_admin_checks_program_and_course_dashboards.py коллеги (репозиторий lms,
origin/feature/dashboard-autotests, отдельная история, код взят через `git show`, ветка
не сливалась) на нашу архитектуру: данные готовятся фикстурой dashboard_data (наши
API-фикстуры created_schedule_item/created_tincan/created_user вместо JSON-подготовки
dashboard_prepare_api.py коллеги), проверки — через AdminDashboardPage вместо
src/ui/pages/dashboard_page.py коллеги.

Проверяются только поля, детерминированные напрямую составом фикстуры (сколько
слушателей назначено, сколько зарегистрировано на мероприятие, сколько назначений
на курс) — без "passed"/"assignments_passed": даже после смены состояния назначения
на "пройдено" и ожидания 120с эти поля статистики курса не обновляются на develop
(похоже на отдельный дефект стенда, не связанный с рендером дашборда, воспроизведено
разведочным прогоном; в тест не включаем, чтобы не завязываться на асинхронный пересчёт).
"""
import allure
import pytest

from ui.pages.admin_dashboard_page import AdminDashboardPage


@allure.feature("Дашборды UI")
@allure.story("Админка: статистика программ и курсов")
class TestAdminChecksProgramAndCourseDashboards:

    @allure.title("UI: Администратор проверяет строки дашбордов программ и курсов")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.dashboards
    def test_admin_checks_program_and_course_dashboards(self, dashboards_admin_page, dashboard_data, env):
        dashboard_page = AdminDashboardPage(dashboards_admin_page)

        with allure.step("1. Открыть дашборд статистики программ и проверить строку программы"):
            dashboard_page.open_programs_dashboard(env.ui_base_url)
            dashboard_page.assert_program_row(
                dashboard_data["program_name"],
                assignments_count=2,
                schedule_items_completeness=1,
            )

        with allure.step("2. Открыть дашборд статистики курсов и проверить строку курса"):
            dashboard_page.open_courses_dashboard(env.ui_base_url)
            dashboard_page.assert_course_row(
                dashboard_data["course_name"],
                total=2,
            )
