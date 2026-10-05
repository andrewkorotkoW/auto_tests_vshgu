"""Опрос слушателя (плеер /testing/player): обязательный вопрос в пропускаемой по
последовательности группе не блокирует завершение опроса — если ветвление по ответу
уводит слушателя мимо этой группы, её обязательность не применяется (группа просто
не показывается, см. test_08_*/pass_group_sequence_by_answer).

Перенос test_14_listener_finishes_poll_sequence_with_required_skipped_group.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_08_*, но у вопроса пропускаемой группы дополнительно взведён required=True
(generate_constructor_question_payload/PollsEndpoint.create_question), прохождение —
через feedback_flow.pass_group_sequence_by_answer до целевой группы, затем ответ на
неё и полное завершение опроса (в отличие от test_08_*, где сценарий заканчивается на
проверке видимости целевого вопроса)."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix
from tests.ui.test_constructor.feedback_flow import pass_group_sequence_by_answer


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: последовательность вопросов опроса")
class TestListenerFinishesPollSequenceWithRequiredSkippedGroup:

    @allure.title("UI: Слушатель завершает опрос с последовательностью, минуя группу с обязательным вопросом")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_listener_finishes_poll_sequence_with_required_skipped_group(
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
        first_question_text = f"Автотест_ОбязПропускСтарт_{suffix}"
        skipped_question_text = f"Автотест_ОбязПропускВопрос_{suffix}"
        target_question_text = f"Автотест_ОбязПропускЦель_{suffix}"
        answer_to_target_text = f"Автотест_ОбязПропускНаЦель_{suffix}"
        answer_to_skipped_text = f"Автотест_ОбязПропускНаПропуск_{suffix}"
        target_answer_text = "Целевой ответ"

        with allure.step("1. Создать опрос, включить последовательность вопросов по ответам"):
            poll_data = created_constructor_poll(topic="AQA poll required skipped group topic")
            content_id = poll_data["content_id"]
            sequence_questions_activated(poll_data)

        with allure.step("2. Создать целевую группу и обязательную пропускаемую группу"):
            questions = polls_endpoint.get_questions(content_id)
            assert questions, f"У опроса id={content_id} не найден дефолтный вопрос"
            first_question = questions[0]
            first_group_id = int(first_question["group"]["group_id"])

            target_question = constructor_poll_question(
                content_id,
                text=target_question_text,
                answers=generate_single_choice_answers(target_answer_text, "Целевой альтернативный ответ"),
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
                required=True,
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

        with allure.step("4. Пройти опрос: ветка минует обязательную группу, завершение проходит без ошибок"):
            constructor_player_page.open_by_content_id(env.ui_base_url, content_id)
            constructor_player_page.start()
            pass_group_sequence_by_answer(
                constructor_player_page,
                start_question_text=first_question_text,
                branch_answer_text=answer_to_target_text,
                target_question_text=target_question_text,
                skipped_question_text=skipped_question_text,
            )
            has_next_group = constructor_player_page.answer_current_group(target_answer_text)
            assert not has_next_group, "Целевая группа должна быть последней в этом сценарии"
            constructor_player_page.finish_survey()
            constructor_player_page.assert_no_error_snackbar_visible()
