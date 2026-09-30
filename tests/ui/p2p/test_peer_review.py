"""p2p / слушатель-проверяющий: список чужих работ, форма критериев, редактирование
до и блокировка после финального подтверждения
(docs/test_cases/p2p/04_peer_review.md, TC-P2P-028..031).

Разведка селекторов — ui/pages/practical_task_page.py (блок «Взаимопроверка (p2p):
«Работы на проверку»»), ui/pages/reviewer_page.py — образец структуры, не менялись.
Функциональности ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_p2p.md),
контракт api/endpoints/p2p.py не подтверждён. Тесты пропускаются без P2P_READY, см.
tests/ui/p2p/conftest.py.
"""
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


def _find_work_id(api_client, homework_id: int, user_id: int) -> int:
    """Находит id ответа (work_id) конкретного пользователя по ПЗ через
    GET /homework/answers?filters[homework_id] — тот же приём, что и в
    tests/api/users/teacher/test_examine_by_teacher.py."""
    answers = api_client.get(f"/homework/answers?filters[homework_id]={homework_id}").json().get("data", [])
    for answer in answers:
        if answer.get("attributes", {}).get("user_id") == user_id:
            return answer["id"]
    pytest.fail(f"Не найден ответ пользователя {user_id} по ПЗ {homework_id}")


def _submit_own_answer(page, env, user, program_name, pz_name, text):
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()

    task_page = PracticalTaskPage(page)
    task_page.open_programs_list(env.ui_base_url)
    task_page.open_program(program_name)
    task_page.open_courses_and_tests_tab()
    task_page.open_practical_task(pz_name)
    task_page.fill_answer(text)
    task_page.submit()
    task_page.expect_sent_to_review()
    return task_page


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Слушатель-проверяющий: список работ и форма критериев")
class TestPeerReview:

    @allure.title("Слушателю-проверяющему показываются только чужие работы, собственная — не выводится")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_peer_reviewer_sees_only_others_works(self, browser, env, api_client, tincan_endpoint,
                                                    assignments_endpoint, created_user, p2p_practical_task,
                                                    p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить поток, P2P-ПЗ, автора и слушателя-проверяющего через API"):
            author = created_user()
            reviewer_listener = created_user()

            cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
            archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
            stream, module, homework = p2p_practical_task(cover_uuid=cover_uuid, archive_uuid=archive_uuid)

            assignments_endpoint.assign(stream["program_id"], stream["id"], [author["id"], reviewer_listener["id"]])
            p2p_endpoint.set_stream_participants(
                stream["program_id"], stream["id"], homework["id"], [author["id"], reviewer_listener["id"]]
            )
            prepare_user_for_tests_via_api(env, author["email"], author["password"])
            prepare_user_for_tests_via_api(env, reviewer_listener["email"], reviewer_listener["password"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

        with allure.step("2. Автор и слушатель-проверяющий сдают собственные работы (служебный шаг)"):
            for context_user, text in (
                (author, "Автотест: ответ автора"),
                (reviewer_listener, "Автотест: ответ слушателя-проверяющего"),
            ):
                context = browser.new_context(viewport={"width": 1366, "height": 768})
                page = context.new_page()
                try:
                    _submit_own_answer(page, env, context_user, program_name, homework["name_client"], text)
                finally:
                    context.close()

        with allure.step("3. Администратор назначает слушателю-проверяющему работу автора"):
            author_work_id = _find_work_id(api_client, homework["id"], author["id"])
            p2p_endpoint.assign_work_manually(
                stream["program_id"], stream["id"], homework["id"], author_work_id, reviewer_listener["id"]
            )

        with allure.step("4. Слушатель-проверяющий открывает раздел «Работы на проверку»"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                LoginPage(page).login(reviewer_listener["email"], reviewer_listener["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                task_page.open_program(program_name)
                task_page.open_courses_and_tests_tab()
                task_page.open_practical_task(homework["name_client"])
                task_page.open_peer_review_works_tab()

                with allure.step("5. Проверить, что видна только чужая работа автора"):
                    author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"
                    reviewer_full_name = f"{reviewer_listener['surname']} {reviewer_listener['name']} {reviewer_listener['patronymic']}"
                    expect(task_page.peer_review_work_row(author_full_name)).to_be_visible(timeout=30000)
                    expect(task_page.peer_review_work_row(reviewer_full_name)).to_have_count(0)
            finally:
                context.close()

    @allure.title("Слушатель-проверяющий открывает назначенную работу и заполняет форму критериев")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_peer_reviewer_fills_criteria_form(self, browser, env, api_client, tincan_endpoint,
                                                 assignments_endpoint, created_user, p2p_practical_task, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить P2P-ПЗ, автора и слушателя-проверяющего, назначить работу"):
            author = created_user()
            reviewer_listener = created_user()

            cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
            archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
            stream, module, homework = p2p_practical_task(cover_uuid=cover_uuid, archive_uuid=archive_uuid)
            p2p_endpoint.set_criteria(homework["id"], [
                {"id": "scale", "type": "scale", "label": "Оценка по шкале"},
                {"id": "single", "type": "single_choice", "label": "Одиночный выбор"},
                {"id": "multi", "type": "multiple_choice", "label": "Множественный выбор"},
                {"id": "comment", "type": "text", "label": "Комментарий"},
            ])

            assignments_endpoint.assign(stream["program_id"], stream["id"], [author["id"], reviewer_listener["id"]])
            prepare_user_for_tests_via_api(env, author["email"], author["password"])
            prepare_user_for_tests_via_api(env, reviewer_listener["email"], reviewer_listener["password"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

            author_context = browser.new_context(viewport={"width": 1366, "height": 768})
            author_page = author_context.new_page()
            try:
                _submit_own_answer(author_page, env, author, program_name, homework["name_client"], "Автотест: ответ автора")
            finally:
                author_context.close()

            author_work_id = _find_work_id(api_client, homework["id"], author["id"])
            p2p_endpoint.assign_work_manually(
                stream["program_id"], stream["id"], homework["id"], author_work_id, reviewer_listener["id"]
            )

        with allure.step("2. Открыть назначенную чужую работу"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                LoginPage(page).login(reviewer_listener["email"], reviewer_listener["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                task_page.open_program(program_name)
                task_page.open_courses_and_tests_tab()
                task_page.open_practical_task(homework["name_client"])
                task_page.open_peer_review_works_tab()
                author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"
                task_page.open_peer_review_work(author_full_name)

                with allure.step("3. Заполнить значения по шкале, вариантам выбора и текстовому полю"):
                    task_page.select_scale_criterion_value("Оценка по шкале", "4")
                    task_page.select_single_choice_criterion("Одиночный выбор", "Вариант 1")
                    task_page.select_multiple_choice_criterion("Множественный выбор", ["Вариант 1", "Вариант 2"])
                    task_page.fill_text_criterion("Комментарий", "Автотест: комментарий проверяющего")
                    task_page.save_peer_review()
            finally:
                context.close()

    @allure.title("До финального подтверждения слушатель-проверяющий может изменить выставленные значения")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_peer_review_editable_before_final_confirmation(self, browser, env, api_client, tincan_endpoint,
                                                               assignments_endpoint, created_user, p2p_practical_task,
                                                               p2p_endpoint):
        """Предусловие: проверка сохранена, но не подтверждена финально."""
        with allure.step("1. Подготовить работу, назначить проверяющего и сохранить (не подтверждённую) проверку"):
            author = created_user()
            reviewer_listener = created_user()

            cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
            archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
            stream, module, homework = p2p_practical_task(cover_uuid=cover_uuid, archive_uuid=archive_uuid)
            p2p_endpoint.set_criteria(homework["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])

            assignments_endpoint.assign(stream["program_id"], stream["id"], [author["id"], reviewer_listener["id"]])
            prepare_user_for_tests_via_api(env, author["email"], author["password"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

            author_context = browser.new_context(viewport={"width": 1366, "height": 768})
            author_page = author_context.new_page()
            try:
                _submit_own_answer(author_page, env, author, program_name, homework["name_client"], "Автотест: ответ автора")
            finally:
                author_context.close()

            author_work_id = _find_work_id(api_client, homework["id"], author["id"])
            p2p_endpoint.assign_work_manually(
                stream["program_id"], stream["id"], homework["id"], author_work_id, reviewer_listener["id"]
            )
            p2p_endpoint.submit_peer_review(author_work_id, reviewer_listener["id"], {"scale": 3}, final_confirm=False)

        with allure.step("2. Вернуться к ранее сохранённой проверке и изменить значение"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                LoginPage(page).login(reviewer_listener["email"], reviewer_listener["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                task_page.open_program(program_name)
                task_page.open_courses_and_tests_tab()
                task_page.open_practical_task(homework["name_client"])
                task_page.open_peer_review_works_tab()
                author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"
                task_page.open_peer_review_work(author_full_name)

                task_page.select_scale_criterion_value("Оценка по шкале", "5")
                task_page.save_peer_review()

                with allure.step("3. Убедиться, что новое значение сохранено"):
                    reviews = p2p_endpoint.get_peer_reviews_for_work(author_work_id)
                    own_review = next(r for r in reviews if r["attributes"]["reviewer_user_id"] == reviewer_listener["id"])
                    assert own_review["attributes"]["criteria_values"]["scale"] == 5
            finally:
                context.close()

    @allure.title("После финального подтверждения проверки редактирование блокируется")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_peer_review_locked_after_final_confirmation(self, browser, env, api_client, tincan_endpoint,
                                                            assignments_endpoint, created_user, p2p_practical_task,
                                                            p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить работу, назначить проверяющего"):
            author = created_user()
            reviewer_listener = created_user()

            cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
            archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
            stream, module, homework = p2p_practical_task(cover_uuid=cover_uuid, archive_uuid=archive_uuid)
            p2p_endpoint.set_criteria(homework["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])

            assignments_endpoint.assign(stream["program_id"], stream["id"], [author["id"], reviewer_listener["id"]])
            prepare_user_for_tests_via_api(env, author["email"], author["password"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

            author_context = browser.new_context(viewport={"width": 1366, "height": 768})
            author_page = author_context.new_page()
            try:
                _submit_own_answer(author_page, env, author, program_name, homework["name_client"], "Автотест: ответ автора")
            finally:
                author_context.close()

            author_work_id = _find_work_id(api_client, homework["id"], author["id"])
            p2p_endpoint.assign_work_manually(
                stream["program_id"], stream["id"], homework["id"], author_work_id, reviewer_listener["id"]
            )

        with allure.step("2. Заполнить форму критериев и выполнить финальное подтверждение"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                LoginPage(page).login(reviewer_listener["email"], reviewer_listener["password"], base_url=env.ui_base_url)
                UserSidebarPage(page).dismiss_popups()

                task_page = PracticalTaskPage(page)
                task_page.open_programs_list(env.ui_base_url)
                task_page.open_program(program_name)
                task_page.open_courses_and_tests_tab()
                task_page.open_practical_task(homework["name_client"])
                task_page.open_peer_review_works_tab()
                author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"
                task_page.open_peer_review_work(author_full_name)

                task_page.select_scale_criterion_value("Оценка по шкале", "4")
                task_page.confirm_peer_review()

                with allure.step("3. Попытаться снова открыть эту проверку на редактирование"):
                    task_page.open_peer_review_works_tab()
                    task_page.open_peer_review_work(author_full_name)
                    task_page.expect_peer_review_locked()
            finally:
                context.close()
