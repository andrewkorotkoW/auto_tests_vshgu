import allure
import pytest

from api.helpers.data_generator import generate_ticket_payload
from api.helpers.expectations import expect_status
from utils.logger import logger


@allure.feature("Обращения в техподдержку")
@allure.story("Создание, статус, закрытие")
class TestTicketsCrudApi:

    @allure.title("POST /tickets от пользователя — обращение создаётся (200/201) и находится в my-tickets")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_ticket(self, user_api_client, tickets_endpoint):
        payload = generate_ticket_payload()
        try:
            with allure.step("Создать обращение POST /tickets — ответ 200/201"):
                resp = user_api_client.post("/tickets", json=payload)
                expect_status(resp, (200, 201))

            with allure.step("Обращение найдено по теме в my-tickets — есть id (create не возвращает id)"):
                ticket = tickets_endpoint.find_by_title(payload["title"])
                assert ticket is not None, f"Обращение с темой {payload['title']} не найдено"
                assert isinstance(ticket["id"], int) and ticket["id"] > 0
                assert ticket["title"] == payload["title"]
                assert ticket["text"] == payload["text"]
        finally:
            # teardown не должен ронять тест: PUT /tickets/{id}/close изредка отвечает
            # 500 "HTTP status code 0 is not valid" на develop (не воспроизводится
            # стабильно — не блокирует основные assert'ы теста выше).
            try:
                found = tickets_endpoint.find_by_title(payload["title"])
                if found is not None:
                    tickets_endpoint.close(found["id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Не удалось закрыть обращение {payload['title']!r} в teardown: {exc}")

    @allure.title("GET /tickets/my-tickets — созданное обращение имеет статус «открыто»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_new_ticket_is_open_in_my_tickets(self, tickets_endpoint, created_ticket):
        ticket = created_ticket()

        with allure.step("Обращение в my-tickets имеет статус open"):
            fetched = tickets_endpoint.find_by_title(ticket["title"])
            assert fetched is not None
            assert fetched["status"] == "open", f"Ожидался статус open, получено {fetched['status']!r}"

    @allure.title("PUT /tickets/{id}/close — обращение закрывается, статус в my-tickets меняется на «закрыто»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_close_ticket(self, tickets_endpoint, created_ticket):
        ticket = created_ticket()

        with allure.step("Закрыть обращение PUT /tickets/{id}/close"):
            resp_data = tickets_endpoint.close(ticket["id"])
            assert resp_data == {"message": "Ok"}

        with allure.step("В my-tickets статус обращения — closed"):
            fetched = tickets_endpoint.find_by_title(ticket["title"])
            assert fetched is not None
            assert fetched["status"] == "closed", f"Ожидался статус closed, получено {fetched['status']!r}"

    @allure.title("Повторное PUT /tickets/{id}/close уже закрытого обращения — фиксируем фактический код")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        reason="Кандидат в дефект (README §13): план ожидал 4xx на повторное закрытие уже "
        "закрытого обращения, стенд develop отвечает 200 {'message': 'Ok'} без ошибки — "
        "повторное закрытие не блокируется.",
        strict=False,
    )
    def test_repeat_close_is_rejected(self, tickets_endpoint, created_ticket):
        ticket = created_ticket()
        tickets_endpoint.close(ticket["id"])

        resp = tickets_endpoint.client.put(f"/tickets/{ticket['id']}/close")
        assert 400 <= resp.status_code < 500, (
            f"Ожидался 4xx на повторное закрытие, получено {resp.status_code}: {resp.text}"
        )

    @allure.title("POST /tickets/{id}/messages в уже закрытое обращение — фиксируем фактический код")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        reason="Кандидат в дефект (README §13): план ожидал 4xx на сообщение в закрытое "
        "обращение, стенд develop отвечает 200 {'message': 'Ok'} — сообщение добавляется "
        "как в открытое обращение.",
        strict=False,
    )
    def test_message_to_closed_ticket_is_rejected(self, tickets_endpoint, created_ticket):
        ticket = created_ticket()
        tickets_endpoint.close(ticket["id"])

        resp = tickets_endpoint.client.post(
            f"/tickets/{ticket['id']}/messages", json={"text": "Автотест сообщение в закрытое обращение"}
        )
        assert 400 <= resp.status_code < 500, (
            f"Ожидался 4xx на сообщение в закрытое обращение, получено {resp.status_code}: {resp.text}"
        )
