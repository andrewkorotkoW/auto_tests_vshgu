"""p2p / регресс обычного ПЗ при выключенной взаимопроверке — UI-часть
(docs/test_cases/p2p/16_regression.md, TC-P2P-108, 109).

Опора на существующие тесты ПЗ (не менялись): tests/ui/practical_tasks/test_complete_practical_task.py,
tests/ui/practical_tasks/test_review_practical_task.py,
tests/ui/practical_tasks/groups/test_group_practical_task_flow.py. Взаимопроверка здесь
намеренно не включается (p2p_endpoint.enable_peer_review не вызывается) — кейсы
проверяют, что появление p2p не ломает штатный (не-P2P) сценарий. Тесты пропускаются
без P2P_READY, см. tests/ui/p2p/conftest.py.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.admin_stream_groups_page import AdminStreamGroupsPage
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.reviewer_page import ReviewerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


def _open_practical_task(page, env, user, program_name, pz_name):
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()

    task_page = PracticalTaskPage(page)
    task_page.open_programs_list(env.ui_base_url)
    task_page.open_program(program_name)
    task_page.open_courses_and_tests_tab()
    task_page.open_practical_task(pz_name)
    return task_page


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Регресс обычного ПЗ без взаимопроверки")
class TestRegression:

    @allure.title("ПЗ с выключенной взаимопроверкой сдаётся и проверяется по прежнему сценарию")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_homework_without_p2p_keeps_standard_flow(self, page, browser, env, api_client, tincan_endpoint,
                                                         assignments_endpoint, homework_endpoint, assigned_user,
                                                         created_module, created_homework, created_user, p2p_endpoint):
        """Предусловие: -"""
        homework_id = None
        try:
            with allure.step("1. Создать обычное ПЗ без включения «Включить взаимопроверку», назначить в поток"):
                assigned = assigned_user()
                user = assigned["user"]
                stream = assigned["stream"]
                reviewer = created_user()
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                homework = created_homework(
                    cover_uuid=cover_uuid, archive_uuid=archive_uuid,
                    teacher_ids=[reviewer["id"]], inspector_ids=[reviewer["id"]],
                )
                homework_id = homework["id"]

                assigned_ok = assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                )
                assert assigned_ok, "Не удалось добавить ПЗ в модуль"

                # Взаимопроверка намеренно не включается — p2p_endpoint.enable_peer_review не вызывается,
                # предмет теста — что этот факт никак не ломает штатный сценарий.
                program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
                user_full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
                prepare_user_for_tests_via_api(env, user["email"], user["password"])

            with allure.step("2. Слушатель сдаёт работу (как в test_complete_practical_task.py)"):
                context = browser.new_context(viewport={"width": 1366, "height": 768})
                student_page = context.new_page()
                try:
                    task_page = _open_practical_task(student_page, env, user, program_name, homework["name_client"])
                    task_page.fill_answer("Автотест: ответ слушателя без взаимопроверки")
                    task_page.submit()
                    task_page.expect_sent_to_review()
                finally:
                    context.close()

            with allure.step(f"3. Проверяющий '{reviewer['email']}' проверяет ответ без участия peer-проверок"):
                LoginPage(page).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

                reviewer_page = ReviewerPage(page)
                reviewer_page.open_practical_tasks_section()
                reviewer_page.open_review(
                    user_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]]
                )
                reviewer_page.review(
                    comment="Автотест: задание проверено без взаимопроверки",
                    file_path=TEST_DATA_DIR / "practical_task_answer.docx",
                    grade="4",
                )

            with allure.step("4. Убедиться, что сценарий прошёл штатно — ПЗ отображается с оценкой 4"):
                reviewer_page.open_answered_tab()
                reviewer_page.expect_answered(
                    user_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]], "4"
                )
        finally:
            if homework_id is not None:
                with allure.step("5. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])

    @allure.title("Групповое ПЗ проходит стандартный сценарий проверки без взаимопроверки")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_group_homework_keeps_standard_flow_without_p2p(self, admin_page, browser, env, api_client,
                                                               tincan_endpoint, assignments_endpoint,
                                                               homework_endpoint, created_stream, created_module,
                                                               created_homework, created_user, p2p_endpoint):
        """Предусловие: -"""
        homework_id = None
        try:
            with allure.step("1. Создать групповое ПЗ без взаимопроверки, назначить в поток и группу"):
                user1 = created_user()
                user2 = created_user()
                reviewer = created_user()
                stream = created_stream()
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                homework = created_homework(
                    cover_uuid=cover_uuid, archive_uuid=archive_uuid,
                    teacher_ids=[reviewer["id"]], inspector_ids=[reviewer["id"]],
                )
                homework_id = homework["id"]
                # Взаимопроверка намеренно не включается.

                assigned_ok = assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                )
                assert assigned_ok, "Не удалось добавить ПЗ в модуль"
                assignments_endpoint.assign(stream["program_id"], stream["id"], [user1["id"], user2["id"]])
                prepare_user_for_tests_via_api(env, user1["email"], user1["password"])
                prepare_user_for_tests_via_api(env, user2["email"], user2["password"])

                program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
                user1_full_name = f"{user1['surname']} {user1['name']} {user1['patronymic']}"

            with allure.step("2. Админка создаёт группу и добавляет в неё ПЗ и обоих слушателей"):
                admin_page.goto(f"{env.ui_base_url}/admin/programs/{stream['program_id']}/streams/{stream['id']}")
                UserSidebarPage(admin_page).dismiss_popups()
                groups_page = AdminStreamGroupsPage(admin_page)
                groups_page.open_groups_tab()
                group_name = f"autotest_p2p_regression_group_{stream['id']}"
                groups_page.create_group_manually(group_name)
                groups_page.open_group(group_name)
                groups_page.add_practical_task(homework["name"])
                groups_page.open_listeners_tab()
                groups_page.add_listener(user1["email"])
                groups_page.add_listener(user2["email"])

            with allure.step(f"3. Первый слушатель '{user1['email']}' отвечает на групповое ПЗ"):
                context1 = browser.new_context(viewport={"width": 1366, "height": 768})
                page1 = context1.new_page()
                try:
                    task_page1 = _open_practical_task(page1, env, user1, program_name, homework["name_client"])
                    task_page1.fill_answer("Автотест: ответ первого участника без взаимопроверки")
                    task_page1.submit()
                    task_page1.expect_sent_to_review()
                finally:
                    context1.close()

            with allure.step(f"4. Проверяющий '{reviewer['email']}' проверяет групповой ответ"):
                context2 = browser.new_context(viewport={"width": 1366, "height": 768})
                page2 = context2.new_page()
                try:
                    LoginPage(page2).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                    UserSidebarPage(page2).dismiss_popups()

                    reviewer_page = ReviewerPage(page2)
                    reviewer_page.open_practical_tasks_section()
                    reviewer_page.open_review(
                        user1_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]]
                    )
                    reviewer_page.review(
                        comment="Автотест: групповое задание проверено без взаимопроверки",
                        file_path=TEST_DATA_DIR / "practical_task_answer.docx",
                        grade="4",
                    )

                    with allure.step("5. Убедиться, что сценарий не затронут появлением p2p"):
                        reviewer_page.open_answered_tab()
                        reviewer_page.expect_answered(
                            user1_full_name, program_name, stream["name"],
                            [homework["name_client"], homework["name"]], "4",
                        )
                finally:
                    context2.close()
        finally:
            if homework_id is not None:
                with allure.step("6. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
