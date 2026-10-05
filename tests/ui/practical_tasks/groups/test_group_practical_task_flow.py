"""Групповое ПЗ: первый слушатель отвечает, второй слушатель видит и редактирует
общий ответ группы, проверяющий проверяет и оценивает групповой ответ.

Перенос сценариев test_15_complete_group_practical_task.py, test_15_1_edit_group_
practical_task_by_second_user.py и test_16_review_group_practical_task.py коллеги
(репозиторий lms, feature/my-tests, см. report.md разд. 2). Поток, модуль, ПЗ и оба
слушателя подняты через наши API-фикстуры; группу в потоке создаёт и наполняет
админка (UI-форма — не предмет этого теста, см. test_create_group_for_stream.py).
Предмет проверки — экраны трёх ролей: два слушателя группы (отдельные Playwright-
контексты) и проверяющий.

Роли user1/user2 авторизуются через отдельные контексты с логином по форме — как
и проверяющий в test_review_practical_task.py. В config/environments.py нет роли
"reviewer" (только "admin"/"user" со своим storage_state) — учётка проверяющего
поднимается так же, как в test_review_practical_task.py: created_user() с
inspector_ids=[...] и логин через LoginPage по email/password, без storage_state.
"""
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.admin_stream_groups_page import AdminStreamGroupsPage
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.reviewer_page import ReviewerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[4] / "test_data"


def _open_group_practical_task(page, env, user, program_name, pz_name):
    """Общий вход слушателя к карточке группового ПЗ: логин → программа → «Курсы и тесты» → ПЗ."""
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()

    task_page = PracticalTaskPage(page)
    task_page.open_programs_list(env.ui_base_url)
    task_page.open_program(program_name)
    task_page.open_courses_and_tests_tab()
    task_page.open_practical_task(pz_name)
    return task_page


@allure.feature("Группы потока UI")
@allure.story("Групповое ПЗ: ответ, редактирование вторым участником, проверка")
class TestGroupPracticalTaskFlow:

    @allure.title("UI: Второй участник группы редактирует общий ответ, проверяющий оценивает групповое ПЗ")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.groups
    def test_group_practical_task_flow(
        self, admin_page, browser, env, api_client, tincan_endpoint, assignments_endpoint,
        created_user, group_practical_task,
    ):
        with allure.step("1. Подготовить поток, модуль, ПЗ, двух слушателей и проверяющего через API"):
            user1 = created_user()
            user2 = created_user()
            reviewer = created_user()

            cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
            archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
            sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_additional_document.xlsx"))

            stream, module, homework = group_practical_task(
                cover_uuid=cover_uuid,
                archive_uuid=archive_uuid,
                sub_files_uuids=[sub_file_uuid],
                teacher_ids=[reviewer["id"]],
                inspector_ids=[reviewer["id"]],
            )

            assignments_endpoint.assign(stream["program_id"], stream["id"], [user1["id"], user2["id"]])

            # Без этого «Моё обучение» показывает только 2 демо-карточки вместо
            # реально назначенной программы (см. test_complete_practical_task.py).
            prepare_user_for_tests_via_api(env, user1["email"], user1["password"])
            prepare_user_for_tests_via_api(env, user2["email"], user2["password"])

            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
            user1_full_name = f"{user1['surname']} {user1['name']} {user1['patronymic']}"

        with allure.step("2. Подготовка: админка создаёт группу, добавляет в неё ПЗ и обоих слушателей"):
            admin_page.goto(f"{env.ui_base_url}/admin/programs/{stream['program_id']}/streams/{stream['id']}")
            UserSidebarPage(admin_page).dismiss_popups()
            groups_page = AdminStreamGroupsPage(admin_page)
            groups_page.open_groups_tab()
            group_name = f"autotest_group_{stream['id']}"
            groups_page.create_group_manually(group_name)
            groups_page.open_group(group_name)
            groups_page.add_practical_task(homework["name"])
            groups_page.open_listeners_tab()
            groups_page.add_listener(user1["email"])
            groups_page.add_listener(user2["email"])

        first_answer = "Автотест: ответ первого участника группы на групповое ПЗ"
        edited_answer = "Автотест: ответ отредактирован вторым участником группы"

        with allure.step(f"3. Первый слушатель '{user1['email']}' отвечает на групповое ПЗ"):
            context1 = browser.new_context(viewport={"width": 1366, "height": 768})
            page1 = context1.new_page()
            try:
                task_page1 = _open_group_practical_task(page1, env, user1, program_name, homework["name_client"])
                task_page1.fill_answer(first_answer)
                task_page1.attach_answer_file(TEST_DATA_DIR / "practical_task_answer.docx")
                task_page1.submit()
                task_page1.expect_sent_to_review()
            finally:
                context1.close()

        with allure.step(f"4. Второй слушатель '{user2['email']}' видит общий ответ и редактирует его"):
            context2 = browser.new_context(viewport={"width": 1366, "height": 768})
            page2 = context2.new_page()
            try:
                task_page2 = _open_group_practical_task(page2, env, user2, program_name, homework["name_client"])
                expect(task_page2.answer_textarea).to_have_value(first_answer, timeout=15000)

                task_page2.start_edit_answer()
                task_page2.edit_answer(edited_answer)
                task_page2.submit()
                task_page2.expect_sent_to_review()
            finally:
                context2.close()

        with allure.step(f"5. Проверяющий '{reviewer['email']}' находит и открывает групповой ответ на проверку"):
            context3 = browser.new_context(viewport={"width": 1366, "height": 768})
            page3 = context3.new_page()
            try:
                LoginPage(page3).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                UserSidebarPage(page3).dismiss_popups()

                reviewer_page = ReviewerPage(page3)
                reviewer_page.open_practical_tasks_section()
                reviewer_page.open_review(
                    user1_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]]
                )

                with allure.step("6. Скачать файл группового ответа"):
                    download = reviewer_page.download_user_answer()
                    logger.info(f"Скачан групповой ответ: {download.suggested_filename}")

                with allure.step("7. Оставить комментарий, прикрепить файл и выставить оценку 4"):
                    reviewer_page.review(
                        comment="Автотест: групповое задание проверено",
                        file_path=TEST_DATA_DIR / "practical_task_answer.docx",
                        grade="4",
                    )

                with allure.step("8. Проверить, что групповое ПЗ отображается во вкладке «Отвечено» с оценкой 4"):
                    reviewer_page.open_answered_tab()
                    reviewer_page.expect_answered(
                        user1_full_name, program_name, stream["name"],
                        [homework["name_client"], homework["name"]], "4",
                    )
            finally:
                context3.close()
