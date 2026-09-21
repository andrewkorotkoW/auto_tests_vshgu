"""Админка: создание программы → потока (все обязательные селекты) → модуля через UI.

Перенос сценария test_02_create_program_stream_module.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Полностью UI-путь администратора — это
единственная форма своего рода (форм создания программы/потока/модуля у нас не было).
Удаление программы (каскадно поток и модуль) — через API-эндпоинт programs.mass_delete.
"""
import datetime as dt

import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.admin_programs_page import AdminProgramsPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("Практические задания UI")
@allure.story("Админка: программа → поток → модуль")
class TestCreateProgramStreamModule:

    @allure.title("UI: Администратор создаёт программу, поток и модуль")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_create_program_stream_module(self, admin_page, env, programs_endpoint):
        programs_page = AdminProgramsPage(admin_page)
        program_id = None

        suffix = unique_suffix()
        program_name = f"Автотест программа {suffix}"
        stream_name = f"Автотест поток {suffix}"
        module_name = f"Автотест модуль {suffix}"

        today = dt.date.today()
        date_from = today.strftime("%d.%m.%Y")
        date_to = (today + dt.timedelta(days=30)).strftime("%d.%m.%Y")

        try:
            with allure.step("1. Создать программу"):
                programs_page.open_list(env.ui_base_url)
                # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
                # закрываем его, иначе затемнение перехватывает клики по форме
                UserSidebarPage(admin_page).dismiss_popups()
                programs_page.create_program(program_name)

            with allure.step("2. Открыть программу и получить её ID"):
                program_id = programs_page.open_program(program_name)
                logger.info(f"Программа создана: ID={program_id}")

            with allure.step("3. Создать поток со всеми обязательными селектами"):
                programs_page.open_create_stream_form()
                stream_id = programs_page.create_stream(
                    name=stream_name,
                    place="Москва",
                    date_from=date_from,
                    date_to=date_to,
                    expert_name=stream_name,
                )
                logger.info(f"Поток создан: ID={stream_id}")

            with allure.step("4. Создать модуль в расписании потока"):
                programs_page.open_schedule_tab()
                programs_page.create_module(
                    name=module_name,
                    place="Онлайн",
                    start_date=date_from,
                    finish_date=date_to,
                )
                logger.info(f"Модуль создан: {module_name}")
        finally:
            if program_id is not None:
                with allure.step("5. Удалить программу (каскадно поток и модуль)"):
                    programs_endpoint.mass_delete([program_id])
