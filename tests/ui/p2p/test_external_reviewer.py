"""p2p / внешний проверяющий по ссылке: список работ, проверка, повторный вход,
отсутствие личного кабинета (docs/test_cases/p2p/05_external_reviewer.md,
TC-P2P-035..037, 039).

Кейсы написаны по приоритетной версии 04 (ссылка многоразовая, внешний видит весь
список сданных работ ПЗ в потоке — известное расхождение с 03/05, см. README).
ui/pages/external_review_page.py открывается в отдельном browser context без
storage_state (без авторизации) — по аналогии с
tests/ui/practical_tasks/groups/test_group_practical_task_flow.py. Функциональности
ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_p2p.md). Тесты
пропускаются без P2P_READY, см. tests/ui/p2p/conftest.py.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.external_review_page import ExternalReviewPage
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from ui.pages.practical_task_page import PracticalTaskPage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


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


def _prepare_stream_with_listeners_and_external_link(browser, env, api_client, tincan_endpoint, assignments_endpoint,
                                                       created_user, p2p_practical_task, p2p_endpoint, listeners_count=2):
    listeners = [created_user() for _ in range(listeners_count)]

    cover_uuid = tincan_endpoint.upload_cover(str(TEST_DATA_DIR / "practical_task_cover.png"))
    archive_uuid = tincan_endpoint.upload_archive(str(TEST_DATA_DIR / "practical_task_main_document.docx"))
    stream, module, homework = p2p_practical_task(cover_uuid=cover_uuid, archive_uuid=archive_uuid)

    assignments_endpoint.assign(stream["program_id"], stream["id"], [u["id"] for u in listeners])
    program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

    for listener in listeners:
        prepare_user_for_tests_via_api(env, listener["email"], listener["password"])
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        try:
            _submit_own_answer(page, env, listener, program_name, homework["name_client"],
                                f"Автотест: ответ слушателя {listener['id']}")
        finally:
            context.close()

    external = p2p_endpoint.add_external_reviewer(
        stream["program_id"], stream["id"], homework["id"], full_name="Автотест Внешний Проверяющий"
    )
    link = p2p_endpoint.get_external_reviewer_link(external["id"])
    return {"stream": stream, "homework": homework, "listeners": listeners, "link": link, "external": external}


@allure.feature("Взаимопроверка ПЗ")
@allure.story("Внешний проверяющий: список работ и проверка по ссылке")
class TestExternalReviewer:

    @allure.title("По персональной ссылке внешний проверяющий видит список всех сданных работ ПЗ в потоке")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_link_shows_all_submitted_works_in_stream(self, browser, env, api_client, tincan_endpoint,
                                                         assignments_endpoint, created_user, p2p_practical_task,
                                                         p2p_endpoint):
        """Предусловие: в потоке несколько слушателей сдали работы по ПЗ."""
        with allure.step("1. Подготовить поток с несколькими сданными работами и персональную ссылку"):
            data = _prepare_stream_with_listeners_and_external_link(
                browser, env, api_client, tincan_endpoint, assignments_endpoint, created_user,
                p2p_practical_task, p2p_endpoint, listeners_count=2,
            )

        with allure.step("2. Открыть персональную ссылку в новом неавторизованном контексте"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                external_page = ExternalReviewPage(page)
                external_page.open_by_link(data["link"])

                with allure.step("3. Проверить, что видны все сданные работы, без запроса логина/пароля"):
                    for listener in data["listeners"]:
                        author_full_name = f"{listener['surname']} {listener['name']} {listener['patronymic']}"
                        assert external_page.work_row(author_full_name).count() == 1
            finally:
                context.close()

    @allure.title("Внешний проверяющий открывает работу, заполняет критерии и переходит к следующей")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_external_reviewer_reviews_work_and_moves_to_next(self, browser, env, api_client, tincan_endpoint,
                                                                 assignments_endpoint, created_user,
                                                                 p2p_practical_task, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить поток с несколькими сданными работами и персональную ссылку"):
            data = _prepare_stream_with_listeners_and_external_link(
                browser, env, api_client, tincan_endpoint, assignments_endpoint, created_user,
                p2p_practical_task, p2p_endpoint, listeners_count=2,
            )
            p2p_endpoint.set_criteria(data["homework"]["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])

        with allure.step("2. По ссылке открыть любую работу из списка"):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                external_page = ExternalReviewPage(page)
                external_page.open_by_link(data["link"])
                first_author = data["listeners"][0]
                first_author_full_name = f"{first_author['surname']} {first_author['name']} {first_author['patronymic']}"
                external_page.open_work(first_author_full_name)

                with allure.step("3. Заполнить критерии и сохранить проверку, перейти к следующей работе"):
                    external_page.select_scale_criterion_value("Оценка по шкале", "5")
                    external_page.save_and_open_next_work()
            finally:
                context.close()

    @allure.title("Повторный переход по той же ссылке возвращает внешнего проверяющего к его списку работ")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_link_reusable_returns_to_work_list(self, browser, env, api_client, tincan_endpoint,
                                                   assignments_endpoint, created_user, p2p_practical_task,
                                                   p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Подготовить поток и персональную ссылку, проверить одну работу, закрыть браузер"):
            data = _prepare_stream_with_listeners_and_external_link(
                browser, env, api_client, tincan_endpoint, assignments_endpoint, created_user,
                p2p_practical_task, p2p_endpoint, listeners_count=1,
            )
            p2p_endpoint.set_criteria(data["homework"]["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])
            author = data["listeners"][0]
            author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"

            context1 = browser.new_context(viewport={"width": 1366, "height": 768})
            page1 = context1.new_page()
            try:
                external_page1 = ExternalReviewPage(page1)
                external_page1.open_by_link(data["link"])
                external_page1.open_work(author_full_name)
                external_page1.select_scale_criterion_value("Оценка по шкале", "4")
                external_page1.save_and_open_next_work()
            finally:
                context1.close()

        with allure.step("2. Снова открыть ту же ссылку"):
            context2 = browser.new_context(viewport={"width": 1366, "height": 768})
            page2 = context2.new_page()
            try:
                external_page2 = ExternalReviewPage(page2)
                external_page2.open_by_link(data["link"])

                with allure.step("3. Убедиться, что ссылка действует повторно и проверенная работа помечена"):
                    external_page2.expect_work_marked_reviewed(author_full_name)
            finally:
                context2.close()

    @allure.title("У внешнего проверяющего нет личного кабинета и статистики")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.p2p
    def test_external_reviewer_has_no_dashboard_or_statistics(self, browser, env, api_client, tincan_endpoint,
                                                                 assignments_endpoint, created_user,
                                                                 p2p_practical_task, p2p_endpoint):
        """Предусловие: -"""
        with allure.step("1. Пройти по персональной ссылке и отправить проверку работы"):
            data = _prepare_stream_with_listeners_and_external_link(
                browser, env, api_client, tincan_endpoint, assignments_endpoint, created_user,
                p2p_practical_task, p2p_endpoint, listeners_count=1,
            )
            p2p_endpoint.set_criteria(data["homework"]["id"], [{"id": "scale", "type": "scale", "label": "Оценка по шкале"}])
            author = data["listeners"][0]
            author_full_name = f"{author['surname']} {author['name']} {author['patronymic']}"

            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()
            try:
                external_page = ExternalReviewPage(page)
                external_page.open_by_link(data["link"])
                external_page.open_work(author_full_name)
                external_page.select_scale_criterion_value("Оценка по шкале", "4")
                external_page.save_and_open_next_work()

                with allure.step("2. Проверить интерфейс на отсутствие личного кабинета/статистики/отчёта"):
                    external_page.expect_no_dashboard_or_statistics()
            finally:
                context.close()
