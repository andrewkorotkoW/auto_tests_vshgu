import allure
import pytest


@allure.feature("Обращения в техподдержку")
@allure.story("Переписка по обращению")
class TestTicketsMessagesApi:

    @allure.title("POST /tickets/{id}/messages — сообщение добавляется (200); GET messages "
                  "возвращает первое и добавленное сообщение в правильном порядке")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_add_message_and_order(self, tickets_endpoint, created_ticket):
        ticket = created_ticket()

        with allure.step("До добавления — в переписке одно (первое) сообщение с текстом обращения"):
            initial_messages = tickets_endpoint.get_messages(ticket["id"])
            assert len(initial_messages) == 1
            assert initial_messages[0]["text"] == ticket["text"]
            first_message_id = initial_messages[0]["message_id"]

        added_text = f"Автотест_ответ_{ticket['id']}"
        with allure.step("Добавить сообщение POST /tickets/{id}/messages — ответ 200"):
            resp_data = tickets_endpoint.add_message(ticket["id"], added_text)
            assert resp_data == {"message": "Ok"}

        with allure.step("GET messages содержит оба сообщения, добавленное — вторым (после первого)"):
            messages = tickets_endpoint.get_messages(ticket["id"])
            assert len(messages) == 2
            assert messages[0]["message_id"] == first_message_id
            assert messages[0]["text"] == ticket["text"]
            assert messages[1]["text"] == added_text
            assert messages[1]["message_id"] != first_message_id
