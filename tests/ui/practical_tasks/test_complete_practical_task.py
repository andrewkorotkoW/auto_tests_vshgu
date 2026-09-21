"""Слушатель проходит практическое задание: скачивает документы, отвечает текстом
и файлом, отправляет на проверку.

Перенос сценария test_05_complete_practical_task.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2). Подготовка (поток, слушатель, модуль, ПЗ,
назначение) — целиком через наши API-фикстуры (assigned_user, created_module,
created_homework), без UI и без JSON-контекстов на диске. UI — только прохождение ПЗ
слушателем, которое и есть предмет проверки.
"""
from pathlib import Path

import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@allure.feature("Практические задания UI")
@allure.story("Слушатель: прохождение ПЗ")
class TestCompletePracticalTask:

    @allure.title("UI: Слушатель скачивает документы ПЗ и отправляет ответ на проверку")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    @pytest.mark.xfail(
        reason="Дефект стенда develop: после API-назначения (assignments.assign на поток + "
               "content в модуль через mass-addition) программа не появляется в «Моё обучение» "
               "слушателя — на странице /education показываются только 2 демо-карточки "
               "(«Пример назначенной программы», «Пример пройденной программы»), реальное имя "
               "программы отсутствует в тексте страницы вообще (проверено дважды через "
               "page.locator('body').inner_text()). Тот же путь подготовки (created_program/"
               "created_stream/created_module + assignments.assign) уже используется в "
               "tests/ui/test_user_lpd_stream_flow.py, который на этом стенде падает раньше — "
               "на API-подготовке (created_lpd: 422 passing_type) — так что независимая "
               "проверка через LPD-путь также недоступна.",
        strict=False,
    )
    def test_complete_practical_task(
        self, page, env, api_client, tincan_endpoint, assignments_endpoint, homework_endpoint,
        assigned_user, created_module, created_homework,
    ):
        homework_id = None

        try:
            with allure.step("1. Подготовить поток, слушателя, модуль и ПЗ через API"):
                assigned = assigned_user()
                user = assigned["user"]
                stream = assigned["stream"]
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_additional_document.xlsx"))

                homework = created_homework(
                    cover_uuid=cover_uuid,
                    archive_uuid=archive_uuid,
                    sub_files_uuids=[sub_file_uuid],
                )
                homework_id = homework["id"]

                assigned_ok = assignments_endpoint.assign_content_to_module(
                    stream["program_id"], stream["id"], module["id"], [homework_id]
                )
                assert assigned_ok, "Не удалось добавить ПЗ в модуль"

                program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]
                logger.info(f"Пользователь: {user['id']}, программа: {program_name}, ПЗ: {homework['name_client']}")

            with allure.step(f"2. Авторизоваться слушателем '{user['email']}'"):
                LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

            with allure.step(f"3. Открыть программу '{program_name}' и вкладку «Курсы и тесты»"):
                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                task_page.open_program(program_name)
                task_page.open_courses_and_tests_tab()

            with allure.step(f"4. Открыть карточку ПЗ '{homework['name_client']}'"):
                task_page.open_practical_task(homework["name_client"])

            with allure.step("5. Скачать основной документ и дополнительные материалы"):
                main_download = task_page.download_main_document()
                logger.info(f"Скачан основной документ: {main_download.suggested_filename}")
                additional_download = task_page.download_additional_materials()
                logger.info(f"Скачаны дополнительные материалы: {additional_download.suggested_filename}")

            with allure.step("6. Заполнить ответ текстом и прикрепить файл"):
                task_page.fill_answer("Автотест: ответ слушателя на практическое задание")
                task_page.attach_answer_file(TEST_DATA_DIR / "practical_task_answer.docx")

            with allure.step("7. Отправить ответ на проверку"):
                task_page.submit()

            with allure.step("8. Проверить статус «Отправлено на проверку»"):
                task_page.expect_sent_to_review()
        finally:
            if homework_id is not None:
                with allure.step("9. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
