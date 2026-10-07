"""Вопрос слушателя через API и рост счётчиков questions_count/answers_count
(docs/ai_chat_recon.md, раздел 2.2: POST /llm-chat/{numeric_llm_chat_id} —
контракт зафиксирован разведкой живым перехватом).

LlmChatEndpoint (api/endpoints/llm_chat.py) не содержит метода для отправки вопроса
слушателя (есть только get/upload_files/setup/disable/remove_file/export/wait_processed/
add_file) — по условиям задачи инфраструктуру не трогаем и не дописываем production-код,
поэтому запрос выполнен напрямую через ApiClient (api_client.post), без изменений
в api/endpoints/llm_chat.py. См. итоговый отчёт: метод ask_question в LlmChatEndpoint
отсутствует, это пробел в инфраструктуре, а не тестов.
"""
import time

import allure
import pytest

from api.helpers.expectations import expect_status
from api.helpers.user_prepare_api import login_user_session
from api.client import ApiClient
from tests.api.ai_chat._helpers import unique_context_file

QUESTION_TEXT = "Из чего варят гороховый суп?"
ANSWER_WAIT_TIMEOUT = 120
ANSWER_POLL_INTERVAL = 5


@allure.feature("Чат с ИИ в курсах")
@allure.story("Вопрос слушателя и счётчики истории")
@pytest.mark.api
@pytest.mark.ai_chat
class TestLlmChatQuestions:

    @allure.title("Вопрос слушателя через API увеличивает questions_count и answers_count")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    def test_questions_count_grows_after_listener_question(
        self, env, api_client, created_tincan, llm_chat_endpoint, tincan_endpoint, prepared_user, tmp_path
    ):
        with allure.step("Создать активити, настроить чат с ИИ и дождаться completed"):
            tincan = created_tincan()
            content_id = tincan["id"]
            context_file = unique_context_file(tmp_path)
            uploaded = llm_chat_endpoint.upload_files([context_file])
            storage_uuid = uploaded[0]["uuid"]
            chat = llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
            chat_id = chat["id"]
            llm_chat_endpoint.wait_processed(content_id)

        with allure.step("Создать слушателя и назначить активити в индивидуальное обучение"):
            listener = prepared_user()
            assigned = tincan_endpoint.assign_activities([content_id], [listener["id"]])
            assert assigned, f"Не удалось назначить активити {content_id} слушателю {listener['id']}"

            listener_session = login_user_session(env, listener["email"], listener["password"])
            listener_client = ApiClient(
                session=listener_session, base_url=env.api_base_url, cookie_name=env.cookie_name
            )

        with allure.step("Запомнить questions_count/answers_count до вопроса"):
            before = llm_chat_endpoint.get(content_id)
            questions_before = before["questions_count"]
            answers_before = before["answers_count"]

        with allure.step("Задать вопрос от имени слушателя: POST /llm-chat/{id}"):
            resp = listener_client.post(f"/llm-chat/{chat_id}", json={"message": QUESTION_TEXT})
            expect_status(resp, 200)

        with allure.step(f"Дождаться роста questions_count/answers_count (до {ANSWER_WAIT_TIMEOUT} с)"):
            deadline = time.monotonic() + ANSWER_WAIT_TIMEOUT
            after = before
            while time.monotonic() < deadline:
                after = llm_chat_endpoint.get(content_id)
                if after["answers_count"] > answers_before:
                    break
                time.sleep(ANSWER_POLL_INTERVAL)

            assert after["questions_count"] > questions_before, (
                f"questions_count не вырос: было {questions_before}, стало {after['questions_count']}"
            )
            assert after["answers_count"] > answers_before, (
                f"answers_count не вырос за {ANSWER_WAIT_TIMEOUT} с: было {answers_before}, "
                f"стало {after['answers_count']}"
            )
