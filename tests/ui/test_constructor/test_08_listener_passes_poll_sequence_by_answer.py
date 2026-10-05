"""Опрос слушателя (плеер /testing/player): последовательность вопросов по ответам —
выбранный вариант ответа в стартовой группе переводит сразу в целевую группу, минуя
промежуточную (пропускаемую).

Перенос test_08_listener_passes_poll_sequence_by_answer.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка опроса
через PollsEndpoint/generate_constructor_question_payload (create_group=True для новых
групп, question_sequence из constructor_sequence_answers — та же схема
source_id/source_type/target_type/target_group_id, что и в tests/api/helpers/
test_constructor_prepare_api.py коллеги), прохождение — через
feedback_flow.pass_group_sequence_by_answer поверх ConstructorPlayerPage.
Открытие опроса — по content_id напрямую (constructor_player_page, без
индивидуального назначения — см. докстринг ConstructorPlayerPage.open_by_content_id)."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix
from tests.ui.test_constructor.feedback_flow import pass_group_sequence_by_answer


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: последовательность вопросов опроса")
class TestListenerPassesPollSequenceByAnswer:

    @allure.title("UI: Слушатель проходит опрос по последовательности вопросов (ветвление по ответу)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_listener_passes_poll_sequence_by_answer(
        self,
        env,
        polls_endpoint,
        created_constructor_poll,
        constructor_poll_question,
        sequence_questions_activated,
        constructor_sequence_answers,
        constructor_player_page,
    ):
        suffix = unique_suffix()
        first_question_text = f"Автотест_СтартВопрос_{suffix}"
        skipped_question_text = f"Автотест_ПропускВопрос_{suffix}"
        target_question_text = f"Автотест_ЦельВопрос_{suffix}"
        answer_to_target_text = f"Автотест_ОтветНаЦель_{suffix}"
        answer_to_skipped_text = f"Автотест_ОтветНаПропуск_{suffix}"

        with allure.step("1. Создать опрос, включить последовательность вопросов по ответам"):
            poll_data = created_constructor_poll(topic="AQA poll sequence topic")
            content_id = poll_data["content_id"]
            sequence_questions_activated(poll_data)

        with allure.step("2. Создать целевую и пропускаемую группы с вопросами"):
            questions = polls_endpoint.get_questions(content_id)
            assert questions, f"У опроса id={content_id} не найден дефолтный вопрос"
            first_question = questions[0]
            first_group_id = int(first_question["group"]["group_id"])

            target_question = constructor_poll_question(
                content_id,
                text=target_question_text,
                answers=generate_single_choice_answers("Целевой ответ", "Целевой альтернативный ответ"),
                order=3,
                create_group=True,
                group_title="Целевая группа",
            )
            target_group_id = int(target_question["group"]["group_id"])

            skipped_question = constructor_poll_question(
                content_id,
                text=skipped_question_text,
                answers=generate_single_choice_answers("Промежуточный ответ", "Промежуточный альтернативный ответ"),
                order=2,
                create_group=True,
                group_title="Пропускаемая группа",
            )
            skipped_group_id = int(skipped_question["group"]["group_id"])

        with allure.step("3. Настроить ветвление стартовой группы по ответам"):
            branch_answers = generate_single_choice_answers(answer_to_target_text, answer_to_skipped_text)
            question_sequence = constructor_sequence_answers(branch_answers, [target_group_id, skipped_group_id])

            constructor_poll_question(
                content_id,
                text=first_question_text,
                question_id=first_question["question_id"],
                group_id=first_group_id,
                order=1,
                answers=branch_answers,
                question_sequence=question_sequence,
            )

        with allure.step("4. Пройти опрос: ответ должен перевести сразу в целевую группу"):
            constructor_player_page.open_by_content_id(env.ui_base_url, content_id)
            constructor_player_page.start()
            pass_group_sequence_by_answer(
                constructor_player_page,
                start_question_text=first_question_text,
                branch_answer_text=answer_to_target_text,
                target_question_text=target_question_text,
                skipped_question_text=skipped_question_text,
            )
