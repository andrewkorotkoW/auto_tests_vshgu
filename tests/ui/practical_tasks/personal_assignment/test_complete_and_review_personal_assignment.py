"""Индивидуально назначенное ПЗ: слушатель проходит его из «Индивидуальное обучение»,
проверяющий проверяет ответ.

Перенос сценариев test_12/test_13 коллеги (репозиторий lms, feature/my-tests, см.
report.md разд. 2). Назначение поднято через API (assignments.assign_to_individual),
без прогона test_assign_from_user_card.py — эта форма уже проверена отдельным тестом.

Коллега пометил свой test_13 как skip с причиной "BUG: reviewer does not receive access
to homework review queue for personal assignments" — проверяющий не видит очередь
проверки индивидуально назначенных ПЗ. Если дефект стенда воспроизводится и у нас,
шаг проверки помечен xfail с той же причиной.
"""
from pathlib import Path

import allure
import pytest

from api.endpoints.assignments import AssignmentsEndpoint
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.reviewer_page import ReviewerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[4] / "test_data"

REVIEWER_QUEUE_BUG_REASON = (
    "Известный дефект стенда: проверяющий не видит очередь проверки индивидуально "
    "назначенных ПЗ (см. report.md разд. 2: коллега пометил test_13 "
    "'BUG: reviewer does not receive access to homework review queue for personal assignments')"
)


@allure.feature("Практические задания UI")
@allure.story("Индивидуальное назначение: прохождение и проверка")
class TestCompleteAndReviewPersonalAssignment:

    @allure.title("UI: Слушатель проходит индивидуальное ПЗ из «Индивидуальное обучение», проверяющий его проверяет")

    @pytest.mark.xfail(

        strict=False,

        reason=(

            "Дефект develop (совпадает с пометкой коллеги на test_13): проверяющий, назначенный на "

            "индивидуальное ПЗ (teacher_ids/inspector_ids), не получает раздел «Практические задания» — "

            "после входа видит обычный кабинет слушателя «У вас нет программ». Шаги 1–6 (слушатель "

            "скачивает материалы, отвечает, отправляет на проверку) проходят; для потокового ПЗ тот же "

            "проверяющий раздел получает (test_review_practical_task зелёный). Проверено 24.09.2026."

        ),

    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.practical_tasks
    def test_complete_and_review_personal_assignment(
        self, page, env, api_client, tincan_endpoint, homework_endpoint,
        created_user, created_homework,
    ):
        homework_id = None

        try:
            with allure.step("1. Подготовить слушателя, проверяющего, ПЗ и индивидуальное назначение через API"):
                user = created_user()
                reviewer = created_user()
                # Без этого «Индивидуальное обучение» показывает «У вас нет программ» вместо
                # реально назначенного ПЗ (тот же класс дефекта, что и в
                # test_complete_practical_task.py — стенду нужно закрытое согласие на ПД
                # и онбординг-истории через API, а не через UI-тур при логине).
                prepare_user_for_tests_via_api(env, user["email"], user["password"])

                cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
                # upload_archive() шлёт файл на /upload/course_archive (только zip/rar) —
                # для «Основного документа» ПЗ стенд принимает файлы через
                # /upload/schedule_item_files, тот же эндпоинт, что и upload_sub_file.
                archive_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
                sub_file_uuid = tincan_endpoint.upload_sub_file(str(TEST_DATA_DIR / "practical_task_additional_document.xlsx"))

                homework = created_homework(
                    cover_uuid=cover_uuid,
                    archive_uuid=archive_uuid,
                    sub_files_uuids=[sub_file_uuid],
                    teacher_ids=[reviewer["id"]],
                    inspector_ids=[reviewer["id"]],
                )
                homework_id = homework["id"]

                assignments_ep = AssignmentsEndpoint(api_client)
                assigned_ok = assignments_ep.assign_to_individual([homework_id], [user["id"]])
                assert assigned_ok, "Не удалось назначить ПЗ индивидуально"

                user_full_name = f"{user['surname']} {user['name']} {user['patronymic']}"
                logger.info(f"Слушатель: {user['id']}, проверяющий: {reviewer['id']}, ПЗ: {homework_id}")

            with allure.step(f"2. Авторизоваться слушателем '{user['email']}'"):
                LoginPage(page).login(
                    user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False
                )
                UserSidebarPage(page).dismiss_popups()

            with allure.step("3. Открыть «Индивидуальное обучение» → «Курсы и тесты» → карточку ПЗ"):
                task_page = PracticalTaskPage(page)
                # «Индивидуальное обучение» -> /education/personal/schedule (тур раздела) ->
                # вкладка «Курсы и тесты» -> /education/personal/activities, где отображается
                # назначенное ПЗ (карточка ищется по name_client ИЛИ name — см. practical_task_page)
                UserSidebarPage(page).open_individual_tab("Курсы и тесты")
                task_page.open_practical_task([homework["name_client"], homework["name"]])

            with allure.step("4. Скачать основной документ и дополнительные материалы"):
                task_page.download_main_document()
                task_page.download_additional_materials()

            with allure.step("5. Заполнить ответ текстом и прикрепить файл, отправить на проверку"):
                task_page.fill_answer("Автотест: ответ на индивидуальное практическое задание")
                task_page.attach_answer_file(TEST_DATA_DIR / "practical_task_answer.docx")
                task_page.submit()
                task_page.expect_sent_to_review()

            with allure.step(f"6. Выйти и авторизоваться проверяющим '{reviewer['email']}'"):
                page.context.clear_cookies()
                LoginPage(page).login(reviewer["email"], reviewer["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

            with allure.step("7. Перейти в раздел «Практические задания» и открыть индивидуальное ПЗ на проверку"):
                reviewer_page = ReviewerPage(page)
                reviewer_page.open_practical_tasks_section()
                try:
                    reviewer_page.open_personal_review(
                        user_full_name, [homework["name_client"], homework["name"]]
                    )
                except AssertionError as exc:
                    pytest.xfail(f"{REVIEWER_QUEUE_BUG_REASON}: {exc}")

            with allure.step("8. Скачать ответ, оставить комментарий и файл, выставить оценку 4"):
                reviewer_page.download_user_answer()
                reviewer_page.review(
                    comment="Автотест: индивидуальное ПЗ проверено",
                    file_path=TEST_DATA_DIR / "practical_task_answer.docx",
                    grade="4",
                )

            with allure.step("9. Проверить, что ПЗ отображается во вкладке «Отвечено» с оценкой 4"):
                reviewer_page.open_answered_tab()
                reviewer_page.expect_personal_answered(
                    user_full_name, [homework["name_client"], homework["name"]], "4"
                )
        finally:
            if homework_id is not None:
                with allure.step("10. Удалить ПЗ"):
                    homework_endpoint.mass_delete([homework_id])
