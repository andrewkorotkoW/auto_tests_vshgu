"""Админка → «Конструктор тестов и опросов»: админ добавляет готовый вопрос из банка
вопросов в целевой опрос списком и видит связь вопроса с банком — тот же сценарий,
что и test_07_* для тестов, но с опросами (банк хранит вопросы тестов и опросов
раздельно по entity_type, см. QuestionBankEndpoint.add_question_to_bank).

Перенос test_11_admin_adds_poll_question_from_bank_to_poll.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: донорский вопрос
готовится через PollsEndpoint/generate_constructor_question_payload (группа
обязательна для опросов), в банк добавляется через QuestionBankEndpoint с
entity_type="poll" и parent_id=None (как и для test — с content_id вместо parent_id
бэкенд отвечает 422, разведано на develop для test_07_*, тот же принцип для poll)."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Банк вопросов")
class TestAdminAddsPollQuestionFromBankToPoll:

    @allure.title("UI: Администратор добавляет вопрос из банка вопросов в опрос")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_adds_poll_question_from_bank_to_poll(
        self,
        constructor_admin_page,
        env,
        polls_endpoint,
        created_constructor_poll,
        constructor_poll_question,
        bank_question,
    ):
        bank_question_text = f"Автотест_ОпросВопросИзБанка_{unique_suffix()}"

        with allure.step("1. Создать донорский опрос и вопрос, добавить его в банк"):
            donor = created_constructor_poll(topic="AQA poll question bank donor topic")
            donor_questions = polls_endpoint.get_questions(donor["content_id"])
            assert donor_questions, f"У донорского опроса id={donor['content_id']} не найден дефолтный вопрос"
            donor_question = donor_questions[0]
            group_id = int(donor_question["group"]["group_id"])

            updated_question = constructor_poll_question(
                donor["content_id"],
                text=bank_question_text,
                question_id=donor_question["question_id"],
                group_id=group_id,
                order=1,
            )
            bank_question(updated_question["question_id"], entity_type="poll", parent_id=None)

        with allure.step("2. Создать целевой опрос"):
            target = created_constructor_poll(topic="AQA poll question bank target topic")

        with allure.step("3. Открыть целевой опрос в конструкторе и добавить вопрос из банка"):
            constructor_admin_page.open_constructor_by_id(env.ui_base_url, target["content_id"])
            constructor_admin_page.add_question_from_bank_as_list(bank_question_text)
            constructor_admin_page.assert_bank_question_added_to_constructor(bank_question_text)
