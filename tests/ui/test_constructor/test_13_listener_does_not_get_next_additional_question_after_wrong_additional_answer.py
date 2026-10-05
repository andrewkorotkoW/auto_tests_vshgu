"""Тест слушателя (плеер /testing/player): после неверного ответа на основной вопрос
слушатель получает первый дополнительный вопрос по теме — но, ошибившись и в нём,
НЕ получает второй дополнительный вопрос из того же набора (в отличие от test_09_*,
где оба дополнительных отвечены верно и показаны по очереди): тест сразу завершается.

Перенос test_13_listener_does_not_get_next_additional_question_after_wrong_additional_answer.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_09_* (та же последовательность PUT, разведано на develop), открытие — по
content_id напрямую (constructor_player_page, без индивидуального назначения — этот
регрессионный сценарий не завязан на статистику/ФИО, в отличие от test_10_*)."""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Слушатель: дополнительные вопросы по теме")
class TestListenerDoesNotGetNextAdditionalQuestionAfterWrongAdditionalAnswer:

    @allure.title("UI: Слушатель не получает следующий доп. вопрос после неверного ответа на предыдущий доп. вопрос")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_listener_does_not_get_next_additional_question_after_wrong_additional_answer(
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
        main_question_text = f"Автотест_РегрессияОсновной_{suffix}"
        first_additional_text = f"Автотест_РегрессияДоп1_{suffix}"
        second_additional_text = f"Автотест_РегрессияДоп2_{suffix}"
        additional_correct_answer_text = "Дополнительный верный ответ"
        additional_wrong_answer_text = "Дополнительный неверный ответ"

        with allure.step("1. Создать тему вопроса и тест, включить доп. вопросы"):
            theme = created_question_theme()
            test_data = created_constructor_test(topic="AQA additional question regression topic")
            content_id = test_data["content_id"]
            extra_questions_activated(test_data)

        with allure.step("2. Подготовить основной вопрос с двумя дополнительными по теме"):
            questions = tests_endpoint.get_questions(content_id)
            assert questions, f"У теста id={content_id} не найден дефолтный вопрос"
            main_question = questions[0]
            group_id = int(main_question["group"]["group_id"])

            additional_answers = generate_single_choice_answers(additional_correct_answer_text, additional_wrong_answer_text)
            constructor_test_question(content_id, text=first_additional_text, answers=additional_answers, tag_id=theme["id"], group_id=None, order=2)
            constructor_test_question(content_id, text=second_additional_text, answers=additional_answers, tag_id=theme["id"], group_id=None, order=3)

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

        with allure.step("3. Пройти тест: неверный основной → неверный первый доп. → тест завершается без второго доп."):
            constructor_player_page.open_by_content_id(env.ui_base_url, content_id)
            constructor_player_page.start()
            constructor_player_page.assert_question_visible(main_question_text)
            constructor_player_page.answer_question("Неверный ответ")

            constructor_player_page.go_to_next_question()
            constructor_player_page.assert_question_visible(first_additional_text)
            constructor_player_page.answer_question(additional_wrong_answer_text)

            constructor_player_page.assert_question_not_visible(second_additional_text)
            constructor_player_page.finish_test()
            constructor_player_page.assert_no_error_snackbar_visible()
