"""Проверяющий проверяет ответ слушателя на ПЗ: находит по ФИО/программе/потоку,
скачивает ответ, оставляет комментарий и файл, выставляет оценку.

Перенос сценария test_06_review_practical_task.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Роль проверяющего (inspector_ids) назначается
через API при подготовке ПЗ. Чтобы у проверяющего было что проверять, слушатель отправляет
ответ через отдельный (служебный) браузерный контекст — это часть подготовки данных,
а не предмет теста; предмет теста — экран проверяющего.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.reviewer_page import ReviewerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


def _submit_student_answer(browser, env, user, program_name, pz_name):
    """Служебный шаг подготовки: слушатель отправляет ответ в отдельном контексте браузера,
    чтобы у проверяющего было что проверять. Не часть проверяемого сценария."""
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    student_page = context.new_page()
    try:
        LoginPage(student_page).login(user["email"], user["password"], base_url=env.ui_base_url)
        UserSidebarPage(student_page).dismiss_popups()

        task_page = PracticalTaskPage(student_page)
        task_page.open_programs_list(env.ui_base_url)
        task_page.open_program(program_name)
        task_page.open_courses_and_tests_tab()
        task_page.open_practical_task(pz_name)
        task_page.fill_answer("Автотест: ответ слушателя для проверки")
        task_page.attach_answer_file(TEST_DATA_DIR / "practical_task_answer.docx")
        task_page.submit()
        task_page.expect_sent_to_review()
    finally:
        context.close()


@allure.feature("Практические задания UI")
@allure.story("Проверяющий: проверка ответа на ПЗ")
class TestReviewPracticalTask:

    @allure.title("UI: Проверяющий проверяет ответ слушателя на ПЗ и выставляет оценку")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    @pytest.mark.e2e
    def test_review_practical_task(
        self, page, browser, env, api_client, tincan_endpoint, assignments_endpoint,
        users_endpoint, assigned_user, created_module, created_homework, prepared_user,
        register_practical_homework,
    ):
        homework_id = None

        try:
            with allure.step("1. Подготовить поток, слушателя, модуль, ПЗ и проверяющего через API"):
                assigned = assigned_user()
                user = assigned["user"]
                stream = assigned["stream"]
                # prepared_user: анкета и все истории онбординга закрыты через API — у проверяющего
                # в UI нечему всплывать, dismiss_popups после логина отрабатывает за секунды.
                reviewer = prepared_user()
                users_endpoint.assign_roles(reviewer["id"], [4])
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_additional_document.xlsx"))

                homework = created_homework(
                    cover_uuid=cover_uuid,
                    archive_uuid=archive_uuid,
                    sub_files_uuids=[sub_file_uuid],
                    teacher_ids=[reviewer["id"]],
                    inspector_ids=[reviewer["id"]],
                )
                homework_id = homework["id"]
                register_practical_homework(homework_id)

                assigned_ok = assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                )
                assert assigned_ok, "Не удалось добавить ПЗ в модуль"

                program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
                user_full_name = f"{user['surname']} {user['name']} {user['patronymic']}"

                # Без этого «Моё обучение» показывает только 2 демо-карточки вместо
                # реально назначенной программы (см. test_complete_practical_task.py).
                prepare_user_for_tests_via_api(env, user["email"], user["password"])

            with allure.step("2. Подготовка: слушатель отправляет ответ на ПЗ (служебный шаг)"):
                _submit_student_answer(browser, env, user, program_name, homework["name_client"])

            with allure.step(f"3. Авторизоваться проверяющим '{reviewer['email']}'"):
                LoginPage(page).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

            with allure.step("4. Перейти в раздел «Практические задания»"):
                reviewer_page = ReviewerPage(page)
                reviewer_page.open_practical_tasks_section()

            with allure.step(f"5. Найти ПЗ по ФИО '{user_full_name}', программе и потоку и открыть на проверку"):
                reviewer_page.open_review(
                    user_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]]
                )

            with allure.step("6. Скачать файл ответа слушателя"):
                download = reviewer_page.download_user_answer()
                logger.info(f"Скачан ответ слушателя: {download.suggested_filename}")

            with allure.step("7. Оставить комментарий, прикрепить файл и выставить оценку 4"):
                reviewer_page.review(
                    comment="Автотест: задание проверено",
                    file_path=TEST_DATA_DIR / "practical_task_answer.docx",
                    grade="4",
                )

            with allure.step("8. Проверить, что ПЗ отображается во вкладке «Отвечено» с оценкой 4"):
                reviewer_page.open_answered_tab()
                reviewer_page.expect_answered(
                    user_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]], "4"
                )
        finally:
            pass
