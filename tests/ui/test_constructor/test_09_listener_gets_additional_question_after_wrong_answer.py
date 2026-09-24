"""Тест слушателя (плеер /testing/player): после неверного ответа на основной вопрос
по очереди появляются дополнительные вопросы по теме (столько, сколько задано
additional_questions_count), верный ответ на последнем завершает тест.

Перенос test_09_listener_gets_additional_question_after_wrong_answer.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка теста —
как в test_02_*/test_06_* (та же последовательность PUT, разведано на develop),
прохождение — через feedback_flow.pass_test_with_additional_questions поверх
ConstructorPlayerPage. В отличие от коллеги (индивидуальное назначение +
launch_url), открываем тест по content_id напрямую (constructor_player_page) — этого
достаточно, индивидуальное назначение не требуется (см. докстринг
ConstructorPlayerPage.open_by_content_id). Все дополнительные вопросы используют
один и тот же верный ответ (helper pass_test_with_additional_questions принимает
единый additional_correct_answer_text на все допвопросы)."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix
from tests.ui.test_constructor.feedback_flow import pass_test_with_additional_questions


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: дополнительные вопросы по теме")
class TestListenerGetsAdditionalQuestionAfterWrongAnswer:

    @allure.title("UI: Слушатель получает дополнительные вопросы после неверного ответа на основной")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_listener_gets_additional_question_after_wrong_answer(
        self,
        env,
        tests_endpoint,
        created_question_theme,
        created_constructor_test,
        constructor_test_question,
        extra_questions_activated,
        constructor_player_page,
    ):
        suffix = unique_suffix()
        main_question_text = f"Автотест_ОсновнойСлушатель_{suffix}"
        first_additional_text = f"Автотест_ДопСлушатель1_{suffix}"
        second_additional_text = f"Автотест_ДопСлушатель2_{suffix}"
        additional_correct_answer_text = "Дополнительный верный ответ"
        additional_wrong_answer_text = "Дополнительный неверный ответ"

        with allure.step("1. Создать тему вопроса и тест, включить доп. вопросы"):
            theme = created_question_theme()
            test_data = created_constructor_test(topic="AQA listener additional question topic")
            content_id = test_data["content_id"]
            extra_questions_activated(test_data)

        with allure.step("2. Подготовить основной вопрос с двумя дополнительными по теме"):
            questions = tests_endpoint.get_questions(content_id)
            assert questions, f"У теста id={content_id} не найден дефолтный вопрос"
            main_question = questions[0]
            group_id = int(main_question["group"]["group_id"])

            additional_answers = generate_single_choice_answers(additional_correct_answer_text, additional_wrong_answer_text)
            constructor_test_question(
                content_id,
                text=first_additional_text,
                answers=additional_answers,
                tag_id=theme["id"],
                group_id=None,
                order=2,
            )
            constructor_test_question(
                content_id,
                text=second_additional_text,
                answers=additional_answers,
                tag_id=theme["id"],
                group_id=None,
                order=3,
            )

            constructor_test_question(
                content_id,
                text=main_question_text,
                question_id=main_question["question_id"],
                group_id=group_id,
                tag_id=theme["id"],
                order=1,
            )
            constructor_test_question(
                content_id,
                text=main_question_text,
                question_id=main_question["question_id"],
                group_id=group_id,
                tag_id=theme["id"],
                order=1,
                additional_questions_count=2,
            )

        with allure.step("3. Пройти тест: неверный основной → два дополнительных вопроса подряд"):
            constructor_player_page.open_by_content_id(env.ui_base_url, content_id)
            constructor_player_page.start()
            pass_test_with_additional_questions(
                constructor_player_page,
                main_question_text=main_question_text,
                wrong_answer_text="Неверный ответ",
                additional_questions=[first_additional_text, second_additional_text],
                additional_correct_answer_text=additional_correct_answer_text,
            )
