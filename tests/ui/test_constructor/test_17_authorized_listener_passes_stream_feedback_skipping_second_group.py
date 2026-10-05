"""АОС потока (плеер /testing/player, публичная ссылка потока): авторизованный
слушатель проходит активную анкету обратной связи, ветка ответа на первую группу
уводит его напрямую в группу «Организация учебного дня», минуя вторую группу
(группу мероприятия 2) целиком — она не показывается. День и модуль (как и в
test_16_*) идут дальше по умолчанию (линейный порядок групп, не переопределённый
веткой ответов).

Перенос test_17_authorized_listener_passes_stream_feedback_skipping_second_group.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_15_*/test_16_* (created_stream_feedback, ветвление через
constructor_poll_question/constructor_sequence_answers), открытие — через публичную
ссылку потока (AosEndpoint.public_link + ConstructorPlayerPage.open_by_launch_url,
как и в test_16_*), а не через ListenerProgramPage/вкладку «Мероприятия» модуля
коллеги — в задаче для этого сценария явно допущена публичная ссылка (см. описание
задачи), а не обязательно путь через личный кабинет слушателя. Проверка пропуска
группы — по маркерному вопросу с уникальным текстом в пропускаемой группе, как и в
test_14_*/pass_group_sequence_by_answer."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix
from ui.pages.login_page import LoginPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: АОС потока с последовательностью вопросов")
class TestAuthorizedListenerPassesStreamFeedbackSkippingSecondGroup:

    @allure.title("UI: Авторизованный слушатель проходит АОС потока, минуя вторую группу вопросов")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_authorized_listener_passes_stream_feedback_skipping_second_group(
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
        feedback_name = f"Автотест_АОСПропуск_{unique_suffix()}"

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

        with allure.step("3. Настроить ветвление: из первой группы — напрямую в день, минуя вторую группу"):
            sequence_questions_activated(flow["attributes"])

            first_question_text = f"Автотест_АОСПропускВетвление_{unique_suffix()}"
            skipped_question_text = f"Автотест_АОСПропускВопрос_{unique_suffix()}"
            answer_to_day_text = f"Автотест_АОСПропускВДень_{unique_suffix()}"

            constructor_poll_question(
                content_id,
                text=skipped_question_text,
                group_id=group1_id,
                order=1006,
            )

            # Второй ответ ведёт в пропускаемую группу (group1_id) — не для того, чтобы
            # им воспользоваться, а чтобы group1 оставалась достижимой хоть по какому-то
            # пути: если ни один ответ не ведёт в неё, бэкенд считает всю
            # последовательность невалидной и отказывает в активации АОС (см. test_18_*,
            # разведано на develop через первый прогон этого файла — activate вернул 400
            # «Данная версия АОС недоступна для активации», когда group1 была полностью
            # недостижима).
            branch_answers = generate_single_choice_answers(answer_to_day_text, "Автотест_АОСПропускАльт")
            constructor_poll_question(
                content_id,
                text=first_question_text,
                group_id=group0_id,
                order=6,
                answers=branch_answers,
                question_sequence=constructor_sequence_answers(branch_answers, [day_group_id, group1_id]),
            )

        with allure.step("4. Активировать АОС на потоке и получить публичную ссылку"):
            assert aos_endpoint.activate(flow["program_id"], flow["stream_id"], content_id), "АОС не активировалась"
            launch_url = aos_endpoint.public_link(flow["program_id"], flow["stream_id"], content_id)

        with allure.step("5. Назначить слушателя на поток и авторизовать"):
            user = prepared_user()
            assignments_endpoint.assign(flow["program_id"], flow["stream_id"], [user["id"]])
            LoginPage(page).login(user["email"], user["password"])
            UserSidebarPage(page).dismiss_popups()

        with allure.step("6. Пройти АОС: ветка минует вторую группу, завершение проходит без ошибок"):
            player_page = ConstructorPlayerPage(page)
            player_page.open_by_launch_url(launch_url, content_id)
            player_page.start()

            player_page.assert_question_visible(first_question_text)
            has_next = player_page.answer_current_group(answer_to_day_text)
            assert has_next, "После первой группы АОС должен быть переход дальше"

            player_page.assert_question_not_visible(skipped_question_text)

            player_page.answer_groups_until_finish()
            player_page.finish_survey()
            player_page.assert_no_error_snackbar_visible()
