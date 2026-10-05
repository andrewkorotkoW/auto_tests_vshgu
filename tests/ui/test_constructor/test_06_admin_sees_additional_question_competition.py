"""Админка → «Конструктор тестов и опросов»: конкуренция двух основных вопросов за
общий дополнительный вопрос по теме — второй основной вопрос не может увеличить
счётчик доп. вопросов, пока единственный тегированный допвопрос занят первым.

Перенос test_06_admin_sees_additional_question_competition.py коллеги
(origin/feature/test-constructor-autotests) — та же последовательность PUT-запросов,
что и в test_02_* (разведано на develop через _scout_constructor2.py), но с двумя
основными вопросами в одной группе."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: дополнительные вопросы по теме")
class TestAdminSeesAdditionalQuestionCompetition:

    @allure.title("UI: Администратор видит конкуренцию основных вопросов за дополнительный")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_sees_additional_question_competition(
        self,
        constructor_admin_page,
        env,
        tests_endpoint,
        created_question_theme,
        created_constructor_test,
        constructor_test_question,
        extra_questions_activated,
    ):
        suffix = unique_suffix()
        first_main_question_text = f"Автотест_ОсновнойПервый_{suffix}"
        second_main_question_text = f"Автотест_ОсновнойВторой_{suffix}"
        additional_question_text = f"Автотест_ДопКонкуренция_{suffix}"

        with allure.step("1. Создать тему вопроса и тест, включить доп. вопросы"):
            theme = created_question_theme()
            test_data = created_constructor_test(topic="AQA constructor competition topic")
            content_id = test_data["content_id"]
            extra_questions_activated(test_data)

        with allure.step("2. Подготовить конкуренцию: доп. вопрос + два основных в одной группе"):
            questions = tests_endpoint.get_questions(content_id)
            assert questions, f"У теста id={content_id} не найден дефолтный вопрос"
            first_main_question = questions[0]
            group_id = int(first_main_question["group"]["group_id"])

            constructor_test_question(
                content_id,
                text=additional_question_text,
                tag_id=theme["id"],
                group_id=None,
                order=3,
            )

            second_main_question = constructor_test_question(
                content_id,
                text=second_main_question_text,
                group_id=group_id,
                tag_id=theme["id"],
                order=2,
            )

            constructor_test_question(
                content_id,
                text=first_main_question_text,
                question_id=first_main_question["question_id"],
                group_id=group_id,
                tag_id=theme["id"],
                order=1,
            )
            constructor_test_question(
                content_id,
                text=first_main_question_text,
                question_id=first_main_question["question_id"],
                group_id=group_id,
                tag_id=theme["id"],
                order=1,
                additional_questions_count=1,
            )
            # Повторно сохраняем второй основной вопрос, чтобы забрать актуальный
            # question_id/order после того, как допвопрос уже занят первым.
            constructor_test_question(
                content_id,
                text=second_main_question_text,
                question_id=second_main_question["question_id"],
                group_id=group_id,
                tag_id=theme["id"],
                order=2,
            )

        with allure.step("3. Открыть тест в конструкторе и проверить конкуренцию за допвопрос"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, content_id)
            constructor_admin_page.assert_additional_question_competition_visible(
                first_main_question_text=first_main_question_text,
                second_main_question_text=second_main_question_text,
            )
