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

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
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
                # Без этого «Моё обучение» показывает только 2 демо-карточки вместо
                # реально назначенной программы — та же подготовка, что и prepared_user
                # (api.helpers.user_prepare_api.prepare_user_for_tests_via_api), но
                # assigned_user не принимает готового пользователя, поэтому готовим его
                # тут же после назначения на поток.
                prepare_user_for_tests_via_api(env, user["email"], user["password"])
                module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                # upload_archive() шлёт файл на /upload/course_archive (только zip/rar) —
                # для «Основного документа» ПЗ (как и для доп. материалов) стенд принимает
                # файлы через /upload/schedule_item_files, тот же эндпоинт, что и upload_sub_file
                # (подтверждено перехватом сетевого запроса при загрузке через админку).
                archive_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
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
                LoginPage(page).login(
                    user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False
                )
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
