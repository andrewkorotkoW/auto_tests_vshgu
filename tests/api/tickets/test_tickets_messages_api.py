import allure
import pytest


@allure.feature("Обращения в техподдержку")
@allure.story("Переписка по обращению")
class TestTicketsMessagesApi:

    @allure.title("POST /tickets/{id}/messages — сообщение добавляется (200); GET messages "
                  "возвращает оба сообщения, новое — первым (порядок по убыванию created_at)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_add_message_and_order(self, tickets_endpoint, created_ticket, env):
        """Порядок — контракт, подтверждённый владельцем 13.10.2026: сообщения отдаются по
        убыванию created_at (новое первым). До 09.10 API отдавал по возрастанию, тест
        закреплял тот порядок — изменение намеренное, см. README (особенности тикетов).
        Релизная сборка на k8s это изменение ещё не содержит (13.10: ASC) — там xfail до
        релиза, см. ветку ниже."""
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

        with allure.step("GET messages содержит оба сообщения, добавленное — первым (новое сверху)"):
            messages = tickets_endpoint.get_messages(ticket["id"])
            assert len(messages) == 2
            if env.name == "k8s" and messages[0]["message_id"] == first_message_id:
                pytest.xfail(
                    "Релизная сборка k8s ещё отдаёт сообщения по возрастанию created_at; "
                    "контракт DESC (новое первым) подтверждён для develop 13.10.2026 — снять после релиза"
                )
            assert messages[0]["text"] == added_text
            assert messages[0]["message_id"] != first_message_id
            assert messages[1]["message_id"] == first_message_id
            assert messages[1]["text"] == ticket["text"]
            assert messages[0]["created_at"] >= messages[1]["created_at"]
