"""Админка → «База Активити»: создание практического задания (тип, обложка, документы,
категория, преподаватель и проверяющий), поиск созданного ПЗ в таблице.

Перенос сценария test_01_create_practical_task.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2) как независимого теста: данные вокруг формы
(преподаватель, проверяющий) готовятся через нашу фикстуру created_user, UI — только
сама форма создания ПЗ, которая и есть предмет проверки.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.admin_activities_page import AdminActivitiesPage
from ui.pages.user_sidebar_page import UserSidebarPage

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@allure.feature("Практические задания UI")
@allure.story("Админка: создание ПЗ в «База Активити»")
class TestCreatePracticalTask:

    @allure.title("UI: Администратор создаёт практическое задание в «База Активити»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_create_practical_task(self, admin_page, env, created_user, register_practical_homework):
        activities_page = AdminActivitiesPage(admin_page)

        with allure.step("1. Подготовить преподавателя и проверяющего через API"):
            teacher = created_user()
            reviewer = created_user()
            teacher_full_name = f"{teacher['surname']} {teacher['name']} {teacher['patronymic']}"
            reviewer_full_name = f"{reviewer['surname']} {reviewer['name']} {reviewer['patronymic']}"

        with allure.step("2. Открыть «База Активити» и форму создания ПЗ"):
            activities_page.open_list(env.ui_base_url)
            # storage_state логинит без формы, поэтому онбординг-тур ещё не пройден —
            # закрываем его, иначе затемнение перехватывает клики по форме
            UserSidebarPage(admin_page).dismiss_popups()
            activities_page.open_create_form()

        with allure.step("3. Заполнить форму ПЗ: тип, обложка, поля, документы, преподаватель, проверяющий"):
            name = f"Автотест ПЗ {unique_suffix()}"
            external_name = f"{name} внешнее"
            activities_page.create_homework_activity(
                name=name,
                external_name=external_name,
                cover_path=TEST_DATA_DIR / "practical_task_cover.png",
                main_document_path=TEST_DATA_DIR / "practical_task_main_document.docx",
                additional_document_path=TEST_DATA_DIR / "practical_task_additional_document.xlsx",
                teacher_full_name=teacher_full_name,
                reviewer_full_name=reviewer_full_name,
            )

        with allure.step("4. Проверить, что ПЗ найдено в таблице «База Активити» по названию"):
            activities_page.expect_created(name)
            homework_id = activities_page.activity_id(name)
            register_practical_homework(homework_id)
