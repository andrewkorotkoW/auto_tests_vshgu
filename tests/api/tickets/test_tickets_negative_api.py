import allure
import pytest

from api.helpers.data_generator import generate_ticket_payload


@allure.feature("Обращения в техподдержку")
@allure.story("Негативные сценарии")
class TestTicketsNegativeApi:

    @allure.title("POST /tickets с пустой темой — 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_empty_title(self, user_api_client):
        # generate_ticket_payload(title="") подставит сгенерированную тему (title="" falsy
        # для его `if not title`) — для пустого поля собираем payload явно.
        base = generate_ticket_payload()
        payload = {"title": "", "text": base["text"], "request_type": base["request_type"]}

        resp = user_api_client.post("/tickets", json=payload)
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text}"
        assert "title" in resp.json().get("errors", {})

    @allure.title("POST /tickets с пустым текстом — 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_empty_text(self, user_api_client):
        base = generate_ticket_payload()
        payload = {"title": base["title"], "text": "", "request_type": base["request_type"]}

        resp = user_api_client.post("/tickets", json=payload)
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text}"
        assert "text" in resp.json().get("errors", {})

    @allure.title("POST /tickets с пустым телом запроса — 422 с ошибками по всем обязательным полям")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.develop
    def test_create_empty_payload(self, user_api_client):
        resp = user_api_client.post("/tickets", json={})
        assert resp.status_code == 422, f"Ожидался 422, получено {resp.status_code}: {resp.text}"
        errors = resp.json().get("errors", {})
        assert "title" in errors
        assert "text" in errors

    @allure.title("GET /tickets/{id}/messages чужого обращения — ожидается 403/404, фиксируем фактический код")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        reason="Подтверждённый IDOR-кандидат (README §13), перепроверено с двумя по-настоящему "
        "разными пользователями (второй создан через UsersEndpoint.create + отдельный логин "
        "config.environments.login, не переиспользует admin_session/user_session, которые на "
        "develop совпадают с одним аккаунтом): GET /tickets/{id}/messages чужого обращения "
        "отвечает 200 с реальной перепиской вместо 403/404.",
        strict=False,
    )
    def test_foreign_ticket_messages_forbidden(self, created_ticket, second_user_tickets_endpoint):
        ticket = created_ticket()

        resp = second_user_tickets_endpoint.client.get(f"/tickets/{ticket['id']}/messages")
        assert resp.status_code in (403, 404), (
            f"Ожидался 403/404 на чужое обращение, получено {resp.status_code}: {resp.text}"
        )

    @allure.title("PUT /tickets/{id}/close чужого обращения — ожидается 403/404, фиксируем фактический код")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.develop
    @pytest.mark.xfail(
        reason="Подтверждённый IDOR-кандидат (README §13): PUT /tickets/{id}/close чужого "
        "обращения отвечает 200 вместо 403/404 — второй пользователь закрывает не своё обращение.",
        strict=False,
    )
    def test_foreign_ticket_close_forbidden(self, created_ticket, second_user_tickets_endpoint):
        ticket = created_ticket()

        resp = second_user_tickets_endpoint.client.put(f"/tickets/{ticket['id']}/close")
        assert resp.status_code in (403, 404), (
            f"Ожидался 403/404 на закрытие чужого обращения, получено {resp.status_code}: {resp.text}"
        )
