"""Админка → «Конструктор тестов и опросов» → АОС потока: админ создаёт анкету
обратной связи по мероприятиям потока и настраивает в ней последовательность
вопросов по ответам, затем активирует анкету на потоке.

Перенос test_15_admin_creates_feedback_with_sequence.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка АОС —
через AosEndpoint.create с двумя очными мероприятиями и is_last_day=True (фикстура
created_stream_feedback в conftest.py) — тот же результат, что и через UI-создание
через вкладку «Анкета обратной связи» потока (ConstructorAdminPage.
start_feedback_creation_from_stream_tab/create_feedback_on_first_step), но без
хождения по этому визарду: бэкенд одинаково генерирует 4 группы вопросов (по одной
на мероприятие + «Организация учебного дня» + «Организация модуля», разведано на
develop через _scout_aos_default.py). Ветвление добавлено через
PollsEndpoint.create_question/constructor_poll_question (как и в test_08_*/test_12_*/
test_14_*), а не через ConstructorAdminPage.add_single_question_to_group — этот метод
уже есть в фундаменте t2, но при реальном прогоне последний из трёх переходов ответа
(target «Завершение теста») не приводит к ожидаемому PUT-запросу внутри
expect_response (Timeout 30000ms), поэтому сам метод не используется здесь (авто-save
после выбора «Завершение теста», по-видимому, не бьёт по /tests/questions/store, в
отличие от переходов на реальную группу) — недостача зафиксирована в отчёте, сам
метод не правился. Проверка последовательности — через
ConstructorAdminPage.question_by_text (в отличие от assert_poll_sequence_settings_visible,
которая берёт «первый» textarea «Вопрос» на странице — здесь это не наш вопрос, а
один из автогенерированных вопросов группы мероприятия)."""
import allure
import pytest
from playwright.sync_api import expect

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: АОС потока с последовательностью вопросов")
class TestAdminCreatesFeedbackWithSequence:

    @allure.title("UI: Администратор создаёт анкету обратной связи потока с последовательностью вопросов")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_creates_feedback_with_sequence(
        self,
        constructor_admin_page,
        env,
        polls_endpoint,
        created_stream_feedback,
        constructor_poll_question,
        sequence_questions_activated,
        constructor_sequence_answers,
    ):
        feedback_name = f"Автотест_АОСПоследовательность_{unique_suffix()}"

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

        with allure.step("3. Включить последовательность вопросов и настроить ветвление первой группы"):
            sequence_questions_activated(flow["attributes"])

            first_question_text = f"Автотест_АОСВетвление_{unique_suffix()}"
            answer_to_second_event_text = f"Автотест_АОСВГруппу2_{unique_suffix()}"
            answer_to_day_text = f"Автотест_АОСВДень_{unique_suffix()}"
            branch_answers = generate_single_choice_answers(answer_to_second_event_text, answer_to_day_text)
            question_sequence = constructor_sequence_answers(branch_answers, [group1_id, day_group_id])

            constructor_poll_question(
                content_id,
                text=first_question_text,
                group_id=group0_id,
                order=6,
                answers=branch_answers,
                question_sequence=question_sequence,
            )

        with allure.step("4. Проверить настройки последовательности в открытом конструкторе"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, content_id)
            constructor_admin_page.assert_sequence_questions_enabled()

            question = constructor_admin_page.question_by_text(first_question_text)
            expect(question.locator('textarea[placeholder="Ответ"]').first).to_have_value(answer_to_second_event_text, timeout=30000)
            expect(question).to_contain_text("Переход к группе", timeout=30000)
            expect(question).to_contain_text(flow["second_event_name"], timeout=30000)

        with allure.step("5. Активировать анкету на потоке"):
            constructor_admin_page.open_stream_feedback_tab(env.ui_base_url, flow["program_id"], flow["stream_id"])
            constructor_admin_page.assert_stream_feedback_row_visible(feedback_name)
            constructor_admin_page.activate_stream_feedback(feedback_name)
