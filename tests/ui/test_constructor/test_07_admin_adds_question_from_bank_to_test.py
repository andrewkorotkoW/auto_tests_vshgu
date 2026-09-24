"""Админка → «Конструктор тестов и опросов»: админ добавляет готовый вопрос из банка
вопросов в целевой тест списком и видит связь вопроса с банком.

Перенос test_07_admin_adds_question_from_bank_to_test.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: донорский вопрос
готовится через TestsEndpoint/generate_constructor_question_payload, в банк
добавляется через QuestionBankEndpoint.add_question_to_bank с parent_id=None (корневая
папка банка — с content_id вместо parent_id бэкенд отвечает 422 «Выбранное значение
для parent id некорректно», разведано на develop через _scout_constructor2.py)."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Банк вопросов")
class TestAdminAddsQuestionFromBankToTest:

    @allure.title("UI: Администратор добавляет вопрос из банка вопросов в тест")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_adds_question_from_bank_to_test(
        self,
        constructor_admin_page,
        env,
        tests_endpoint,
        created_constructor_test,
        constructor_test_question,
        bank_question,
    ):
        bank_question_text = f"Автотест_ВопросИзБанка_{unique_suffix()}"

        with allure.step("1. Создать донорский тест и вопрос, добавить его в банк"):
            donor = created_constructor_test(topic="AQA question bank donor topic")
            donor_questions = tests_endpoint.get_questions(donor["content_id"])
            assert donor_questions, f"У донорского теста id={donor['content_id']} не найден дефолтный вопрос"
            donor_question = donor_questions[0]
            group_id = int(donor_question["group"]["group_id"])

            updated_question = constructor_test_question(
                donor["content_id"],
                text=bank_question_text,
                question_id=donor_question["question_id"],
                group_id=group_id,
                order=1,
            )
            bank_question(updated_question["question_id"], entity_type="test", parent_id=None)

        with allure.step("2. Создать целевой тест"):
            target = created_constructor_test(topic="AQA question bank target topic")

        with allure.step("3. Открыть целевой тест в конструкторе и добавить вопрос из банка"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, target["content_id"])
            constructor_admin_page.add_question_from_bank_as_list(bank_question_text)
            constructor_admin_page.assert_bank_question_added_to_constructor(bank_question_text)
