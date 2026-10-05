"""Админка: добавление слушателя на поток через UI (вкладка «Слушатели»).

Перенос сценария test_04_add_user_to_stream.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Поток и пользователь подняты через наши
фикстуры created_stream/created_user; UI — только модалка добавления слушателя.
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_programs_page import AdminProgramsPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger


@allure.feature("Практические задания UI")
@allure.story("Админка: добавление слушателя на поток")
class TestAddListenerToStream:

    @allure.title("UI: Администратор добавляет слушателя на поток")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_add_listener_to_stream(self, admin_page, env, created_stream, created_user):
        with allure.step("1. Подготовить поток и пользователя через API"):
            stream = created_stream()
            user = created_user()
            user_full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
            logger.info(f"Поток: {stream['id']}, пользователь: {user['id']} ({user_full_name})")

        with allure.step("2. Открыть вкладку «Слушатели» потока"):
            admin_page.goto(f"{env.ui_base_url}/admin/programs/{stream['program_id']}/streams/{stream['id']}")
            # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
            # закрываем его, иначе затемнение перехватывает клики по вкладкам
            UserSidebarPage(admin_page).dismiss_popups()
            programs_page = AdminProgramsPage(admin_page)
            programs_page.open_listeners_tab()

        with allure.step("3. Добавить слушателя через модалку"):
            programs_page.add_listener(user_full_name, user["id"])

        with allure.step("4. Проверить строку слушателя по user_id"):
            expect(programs_page.listener_row(user["id"])).to_be_visible(timeout=15000)
