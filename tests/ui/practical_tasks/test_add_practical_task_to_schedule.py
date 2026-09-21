"""Админка: добавление ПЗ в расписание модуля через модалку «Добавить Активити».

Перенос сценария test_03_add_practical_task_to_module.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Программа/поток/модуль подняты через нашу
фикстуру created_module, ПЗ — через created_homework; UI — только сама модалка
добавления, которая и есть предмет проверки.
"""
import allure
import pytest

from ui.pages.admin_programs_page import AdminProgramsPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("Практические задания UI")
@allure.story("Админка: добавление ПЗ в расписание модуля")
class TestAddPracticalTaskToSchedule:

    @allure.title("UI: Администратор добавляет ПЗ в расписание модуля")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_add_practical_task_to_schedule(self, admin_page, env, created_module, created_homework, homework_endpoint):
        homework_id = None

        try:
            with allure.step("1. Подготовить программу → поток → модуль и ПЗ через API"):
                module = created_module()
                homework = created_homework()
                homework_id = homework["id"]
                logger.info(f"Модуль: {module['id']}, ПЗ: {homework_id} ({homework['name']})")

            with allure.step("2. Открыть расписание потока"):
                admin_page.goto(
                    f"{env.ui_base_url}/admin/programs/{module['program_id']}/streams/{module['stream_id']}"
                )
                # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
                # закрываем его, иначе затемнение перехватывает клики по вкладкам
                UserSidebarPage(admin_page).dismiss_popups()
                programs_page = AdminProgramsPage(admin_page)
                programs_page.open_schedule_tab()

            with allure.step("3. Добавить ПЗ в расписание модуля через модалку"):
                programs_page.add_activity_to_schedule(homework["name"])
        finally:
            if homework_id is not None:
                with allure.step("4. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
