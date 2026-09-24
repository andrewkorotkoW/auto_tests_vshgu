"""Админка → «Конструктор тестов и опросов»: тест с дополнительным вопросом по теме
(появляется после неправильного ответа на основной вопрос).

Перенос test_02_admin_creates_test_with_additional_questions.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: подготовка через
наши фикстуры/эндпоинты (TestsEndpoint, QuestionBankEndpoint,
generate_constructor_question_payload) вместо tests/api/helpers/test_constructor_prepare_api.py
коллеги, но с той же последовательностью PUT-запросов (разведано перед написанием
теста через _scout_constructor2.py на develop): доп. вопрос без группы (group_id=None)
с темой, затем основной вопрос сначала с темой, затем повторным PUT — с
additional_questions_count=1.
"""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: дополнительные вопросы по теме")
class TestAdminCreatesTestWithAdditionalQuestions:

    @allure.title("UI: Администратор создаёт тест с дополнительным вопросом по теме")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_creates_test_with_additional_questions(
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
        main_question_text = f"Автотест_ОсновнойВопрос_{suffix}"
        additional_question_text = f"Автотест_ДопВопрос_{suffix}"

        with allure.step("1. Создать тему вопроса и тест, включить доп. вопросы"):
            theme = created_question_theme()
            test_data = created_constructor_test(topic="AQA constructor topic")
            content_id = test_data["content_id"]
            extra_questions_activated(test_data)

        with allure.step("2. Добавить дополнительный вопрос по теме (без группы)"):
            questions = tests_endpoint.get_questions(content_id)
            assert questions, f"У теста id={content_id} не найден дефолтный вопрос"
            main_question = questions[0]
            group_id = int(main_question["group"]["group_id"])

            constructor_test_question(
                content_id,
                text=additional_question_text,
                tag_id=theme["id"],
                group_id=None,
                order=2,
            )

        with allure.step("3. Привязать тему к основному вопросу и включить счётчик доп. вопросов"):
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
                additional_questions_count=1,
            )

        with allure.step("4. Открыть тест в конструкторе и проверить дополнительный вопрос"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, content_id)
            constructor_admin_page.assert_tagged_additional_questions_visible(
                question_tag_name=theme["name"],
                main_question_text=main_question_text,
                additional_question_text=additional_question_text,
            )
