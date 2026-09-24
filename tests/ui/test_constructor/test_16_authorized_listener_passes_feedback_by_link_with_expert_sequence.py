"""АОС потока (плеер /testing/player, публичная ссылка потока): авторизованный
слушатель проходит активную анкету обратной связи с последовательностью вопросов по
ответам — маршрут ветвления группа мероприятия 1 → группа мероприятия 2 → «Организация
учебного дня», дальше группа «Организация модуля» идёт по умолчанию (линейный порядок
групп, не переопределённый веткой ответов) — отвечаем и на неё перед завершением
(ConstructorPlayerPage.answer_groups_until_finish, разведано на develop).

Перенос test_16_authorized_listener_passes_feedback_by_link_with_expert_sequence.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_15_* (created_stream_feedback, ветвление через constructor_poll_question/
constructor_sequence_answers, а не через add_single_question_to_group — см. докстринг
test_15_*), публичная ссылка — через AosEndpoint.public_link (после
AosEndpoint.activate), открытие — через ConstructorPlayerPage.open_by_launch_url,
авторизация слушателя — prepared_user (снимает блокирующую модалку «данные о себе»)
+ LoginPage, как и в tests/ui/aos/user/test_user_aos_flow.py. В отличие от анонимного
test_aos_public_link.py, авторизованному слушателю публичная ссылка отдаёт редирект на
/education, если он не назначен на поток (assignments_endpoint.assign) — разведано на
develop (первый прогон)."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix
from ui.pages.login_page import LoginPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: АОС потока с последовательностью вопросов")
class TestAuthorizedListenerPassesFeedbackByLinkWithExpertSequence:

    @allure.title("UI: Авторизованный слушатель проходит АОС потока по публичной ссылке с последовательностью вопросов")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_authorized_listener_passes_feedback_by_link_with_expert_sequence(
        self,
        page,
        env,
        polls_endpoint,
        aos_endpoint,
        created_stream_feedback,
        constructor_poll_question,
        sequence_questions_activated,
        constructor_sequence_answers,
        prepared_user,
        assignments_endpoint,
    ):
        feedback_name = f"Автотест_АОСЭксперт_{unique_suffix()}"

        with allure.step("1. Создать АОС потока по двум мероприятиям"):
            flow = created_stream_feedback(name=feedback_name)
            content_id = flow["content_id"]

        with allure.step("2. Найти автосозданные группы мероприятий/дня"):
            questions = polls_endpoint.get_questions(content_id)
            groups = {}
            for question in questions:
                groups.setdefault(question["group_id"], question["group"]["group_title"])

            group0_id = next(gid for gid, title in groups.items() if flow["first_event_name"] in title)
            group1_id = next(gid for gid, title in groups.items() if flow["second_event_name"] in title)
            day_group_id = next(gid for gid, title in groups.items() if title == "Организация учебного дня")

        with allure.step("3. Включить последовательность вопросов и настроить маршрут группа1 → группа2 → день"):
            sequence_questions_activated(flow["attributes"])

            first_question_text = f"Автотест_АОСЭкспертВетвление1_{unique_suffix()}"
            second_question_text = f"Автотест_АОСЭкспертВетвление2_{unique_suffix()}"
            answer_to_second_event_text = f"Автотест_АОСЭкспертВГруппу2_{unique_suffix()}"
            answer_to_day_text = f"Автотест_АОСЭкспертВДень_{unique_suffix()}"

            first_branch_answers = generate_single_choice_answers(answer_to_second_event_text, "Автотест_АОСЭкспертАльт1")
            constructor_poll_question(
                content_id,
                text=first_question_text,
                group_id=group0_id,
                order=6,
                answers=first_branch_answers,
                question_sequence=constructor_sequence_answers(first_branch_answers, [group1_id, group1_id]),
            )

            second_branch_answers = generate_single_choice_answers(answer_to_day_text, "Автотест_АОСЭкспертАльт2")
            constructor_poll_question(
                content_id,
                text=second_question_text,
                group_id=group1_id,
                order=1006,
                answers=second_branch_answers,
                question_sequence=constructor_sequence_answers(second_branch_answers, [day_group_id, day_group_id]),
            )

        with allure.step("4. Активировать АОС на потоке и получить публичную ссылку"):
            assert aos_endpoint.activate(flow["program_id"], flow["stream_id"], content_id), "АОС не активировалась"
            launch_url = aos_endpoint.public_link(flow["program_id"], flow["stream_id"], content_id)

        with allure.step("5. Назначить слушателя на поток и авторизовать"):
            user = prepared_user()
            assignments_endpoint.assign(flow["program_id"], flow["stream_id"], [user["id"]])
            LoginPage(page).login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

        with allure.step("6. Пройти АОС по маршруту группа1 → группа2 → день → завершение"):
            player_page = ConstructorPlayerPage(page)
            player_page.open_by_launch_url(launch_url, content_id)
            player_page.start()

            player_page.assert_question_visible(first_question_text)
            has_next = player_page.answer_current_group(answer_to_second_event_text)
            assert has_next, "После первой группы АОС должен быть переход дальше"

            player_page.assert_question_visible(second_question_text)
            has_next = player_page.answer_current_group(answer_to_day_text)
            assert has_next, "После второй группы АОС должен быть переход дальше"

            # День и модуль не переопределены веткой ответов, поэтому после дня идёт
            # модуль по умолчанию (линейный порядок групп) — отвечаем и на него,
            # прежде чем ждать «Завершить».
            player_page.answer_groups_until_finish()
            player_page.finish_survey()
            player_page.assert_no_error_snackbar_visible()
