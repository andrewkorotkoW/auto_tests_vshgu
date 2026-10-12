"""Проверяющий открывает ответ на ПЗ, у которого есть файл в «Дополнительных материалах».

Сопутствующий баг задачи VSHGU2-1263: на develop при нажатии «Проверить» во вкладке «Новые»
в консоли падает `TypeError: Cannot read properties of undefined (reading 'type')`
(чанк HomeWorkTeacherView), а блок «Дополнительные материалы по заданию» остаётся пустым.
На ветке 1263 исправлено (проверено 29.09.2026), поэтому тест помечен xfail без strict:
на develop до выкатки — xfail, после выкатки — xpass, тогда пометку снять.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from tests.ui.practical_tasks.test_review_practical_task import _submit_student_answer
from ui.pages.login_page import LoginPage
from ui.pages.reviewer_page import ReviewerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger
from playwright.sync_api import expect

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"
ADDITIONAL_FILE = "practical_task_additional_document.xlsx"


@allure.feature("Практические задания UI")
@allure.story("Проверяющий: проверка ответа на ПЗ")
class TestReviewerSeesAdditionalMaterials:

    @allure.title("UI: Проверяющий видит файл доп. материалов ПЗ на странице проверки без ошибок в консоли")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    @pytest.mark.xfail(
        reason=(
            "VSHGU2-1263 (сопутствующий баг): на develop при открытии «Проверить» для ПЗ с файлом в "
            "«Дополнительных материалах» в консоли TypeError (reading 'type'), блок доп. материалов пустой. "
            "Исправлено на ветке 1263, снять xfail после выкатки на develop."
        ),
        strict=False,
    )
    def test_reviewer_sees_additional_materials(
        self, page, browser, env, api_client, tincan_endpoint, assignments_endpoint, homework_endpoint,
        assigned_user, created_module, created_homework, created_user,
    ):
        homework_id = None
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

        try:
            with allure.step("1. Подготовить поток, слушателя, модуль, проверяющего и ПЗ с файлом доп. материалов"):
                assigned = assigned_user()
                user = assigned["user"]
                stream = assigned["stream"]
                reviewer = created_user()
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / ADDITIONAL_FILE))
                homework = created_homework(
                    cover_uuid=cover_uuid,
                    archive_uuid=archive_uuid,
                    sub_files_uuids=[sub_file_uuid],
                    teacher_ids=[reviewer["id"]],
                    inspector_ids=[reviewer["id"]],
                )
                homework_id = homework["id"]
                assert assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                ), "Не удалось добавить ПЗ в модуль"
                program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
                user_full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
                prepare_user_for_tests_via_api(env, user["email"], user["password"])

            with allure.step("2. Подготовка: слушатель отправляет ответ на ПЗ (служебный шаг)"):
                _submit_student_answer(browser, env, user, program_name, homework["name_client"])

            with allure.step(f"3. Авторизоваться проверяющим '{reviewer['email']}' и открыть «Практические задания»"):
                LoginPage(page).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()
                reviewer_page = ReviewerPage(page)
                reviewer_page.open_practical_tasks_section()
                console_errors.clear()

            with allure.step("4. Во вкладке «Новые» нажать «Проверить» у ответа слушателя"):
                reviewer_page.open_review(
                    user_full_name, program_name, stream["name"], [homework["name_client"], homework["name"]]
                )

            with allure.step(f"5. На странице проверки виден файл доп. материалов «{ADDITIONAL_FILE}»"):
                expect(reviewer_page.additional_material_link(ADDITIONAL_FILE)).to_be_visible(timeout=15000)

            with allure.step("6. В консоли браузера нет ошибок после открытия проверки"):
                logger.info(f"Ошибки консоли: {console_errors}")
                assert not console_errors, f"Ошибки в консоли при открытии проверки: {console_errors[:3]}"
        finally:
            if homework_id is not None:
                with allure.step("7. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
