"""Админка → «Конструктор тестов и опросов»: админ видит в конструкторе опроса
настроенную последовательность вопросов по ответам — у ответа стартового вопроса
отображается переход в целевую группу.

Перенос test_12_admin_sees_poll_sequence_settings_in_constructor.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка — та же,
что и в test_08_* (PollsEndpoint/generate_constructor_question_payload,
constructor_sequence_answers для question_sequence), но без прохождения — только
проверка настроек в открытом конструкторе через
ConstructorAdminPage.assert_poll_sequence_settings_visible."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: последовательность вопросов опроса")
class TestAdminSeesPollSequenceSettingsInConstructor:

    @allure.title("UI: Администратор видит настройки последовательности вопросов опроса в конструкторе")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_sees_poll_sequence_settings_in_constructor(
        self,
        constructor_admin_page,
        env,
        polls_endpoint,
        created_constructor_poll,
        constructor_poll_question,
        sequence_questions_activated,
        constructor_sequence_answers,
    ):
        suffix = unique_suffix()
        first_question_text = f"Автотест_НастройкиСтартВопрос_{suffix}"
        skipped_question_text = f"Автотест_НастройкиПропускВопрос_{suffix}"
        target_question_text = f"Автотест_НастройкиЦельВопрос_{suffix}"
        answer_to_target_text = f"Автотест_НастройкиОтветНаЦель_{suffix}"
        answer_to_skipped_text = f"Автотест_НастройкиОтветНаПропуск_{suffix}"

        with allure.step("1. Создать опрос, включить последовательность вопросов по ответам"):
            poll_data = created_constructor_poll(topic="AQA poll sequence settings topic")
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

        with allure.step("4. Открыть опрос в конструкторе и проверить настройки перехода"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, content_id)
            constructor_admin_page.assert_poll_sequence_settings_visible(
                first_question_text=first_question_text,
                answer_text=answer_to_target_text,
                target_group_title="Целевая группа",
            )
