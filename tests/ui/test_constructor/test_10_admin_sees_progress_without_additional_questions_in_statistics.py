"""Админка → «Конструктор тестов и опросов» → Статистика: прогресс слушателя в
статистике не учитывает дополнительные вопросы по теме — они участвуют в попытке,
но не считаются отдельными вопросами теста, поэтому прогресс остаётся 0%, даже если
часть дополнительных вопросов отвечена верно.

Перенос test_10_admin_sees_progress_without_additional_questions_in_statistics.py
коллеги (origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка —
как в test_02_*/test_06_*/test_09_* (та же последовательность PUT, разведано на
develop), назначение слушателю — через PollsEndpoint.assign_activities (инд. трек,
общий для test/poll контента, см. tests/ui/polls/individual/test_poll_flow.py),
прохождение — через ConstructorPlayerPage напрямую (без отдельного helper —
несимметричный сценарий: один доп. вопрос отвечен верно, другой неверно), проверка —
через уже готовые ConstructorAdminPage.open_statistics_for_individual_test/
assert_user_test_progress_visible.
"""
import allure
import pytest

from api.helpers.data_generator import generate_single_choice_answers, unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Статистика: прогресс без учёта дополнительных вопросов")
class TestAdminSeesProgressWithoutAdditionalQuestionsInStatistics:

    @allure.title("UI: Администратор видит прогресс слушателя без учёта доп. вопросов в статистике")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_sees_progress_without_additional_questions_in_statistics(
        self,
        env,
        tests_endpoint,
        polls_endpoint,
        created_question_theme,
        created_constructor_test,
        constructor_test_question,
        extra_questions_activated,
        constructor_listener_page,
        constructor_admin_page,
    ):
        suffix = unique_suffix()
        constructor_name = f"Автотест_Статистика_{suffix}"
        main_question_text = f"Автотест_СтатОсновной_{suffix}"
        first_additional_text = f"Автотест_СтатДоп1_{suffix}"
        second_additional_text = f"Автотест_СтатДоп2_{suffix}"
        additional_correct_answer_text = "Дополнительный верный ответ"
        additional_wrong_answer_text = "Дополнительный неверный ответ"

        with allure.step("1. Создать тему вопроса и тест, включить доп. вопросы"):
            theme = created_question_theme()
            test_data = created_constructor_test(name=constructor_name, topic="AQA statistics topic")
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

        listener_page, listener = constructor_listener_page

        with allure.step("3. Назначить тест слушателю через инд. трек"):
            polls_endpoint.assign_activities([content_id], [listener["id"]])

        with allure.step("4. Пройти тест: основной неверно → доп.1 верно → доп.2 неверно → завершить"):
            listener_page.open_by_content_id(env.ui_base_url, content_id)
            listener_page.start()
            listener_page.assert_question_visible(main_question_text)
            listener_page.answer_question("Неверный ответ")

            listener_page.go_to_next_question()
            listener_page.assert_question_visible(first_additional_text)
            listener_page.answer_question(additional_correct_answer_text)

            listener_page.go_to_next_question()
            listener_page.assert_question_visible(second_additional_text)
            listener_page.answer_question(additional_wrong_answer_text)
            listener_page.finish_test()

        with allure.step("5. Проверить в статистике прогресс 0% без учёта доп. вопросов"):
            full_name = f"{listener['surname']} {listener['name']} {listener['patronymic']}"
            constructor_admin_page.open_statistics_for_individual_test(env.ui_base_url, content_id, constructor_name)
            constructor_admin_page.search_statistics_by_user_name(full_name)
            constructor_admin_page.assert_user_test_progress_visible(full_name, 0)
