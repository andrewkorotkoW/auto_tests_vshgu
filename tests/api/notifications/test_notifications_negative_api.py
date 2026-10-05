import allure
import pytest

from api.client import ApiClient
from api.helpers.data_generator import generate_notification_payload
from api.helpers.expectations import expect_status
from config.environments import LoginError, login


@allure.feature("Уведомления")
@allure.story("Негативные сценарии")
class TestNotificationsNegativeApi:

    @allure.title("POST /notifications/create без получателей — кандидат в дефект (план ждёт 422, факт 201)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Кандидат в дефект: создание уведомления без получателей/программ/потоков "
            "(users=[], programs=[], streams=[]) отвечает 201 и создаёт 'уведомление в никуда' "
            "вместо ожидаемого по мишн-доку 422 — сервер не валидирует наличие хотя бы одной "
            "аудитории у уведомления."
        ),
    )
    def test_create_without_receivers_returns_422(self, api_client, notifications_endpoint):
        payload = generate_notification_payload(users=[], programs=[], streams=[])
        resp = api_client.post("/notifications/create", json=payload)
        created_id = resp.json().get("data", {}).get("id") if resp.status_code in (200, 201) else None
        try:
            assert resp.status_code == 422, f"Ожидали 422, получили {resp.status_code}: {resp.text}"
        finally:
            if created_id:
                try:
                    notifications_endpoint.delete([created_id])
                except Exception:
                    pass

    @allure.title("POST /notifications/create без текста → 422 с сообщением")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_create_without_text_returns_422(self, api_client, created_user):
        receiver = created_user()
        payload = generate_notification_payload(users=[receiver["id"]])
        payload["text"] = ""

        resp = api_client.post("/notifications/create", json=payload)
        expect_status(resp, 422)
        body = resp.json()
        assert body.get("message"), "В ответе 422 нет сообщения об ошибке"
        assert "text" in body.get("errors", {}), "Ошибка валидации не привязана к полю text"

    @allure.title("GET /notifications/{id} от неадресованного пользователя → 403/404")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_get_notification_forbidden_for_unrelated_user(self, env, created_user, created_notification):
        """Свежесозданный обычный пользователь (без админ/менеджерских ролей) не может
        открыть чужое уведомление по id — на develop это проявляется как 403 на весь
        раздел /notifications/* (обычная роль слушателя не имеет прав на этот раздел
        вообще, не только на конкретный чужой id — см. отчёт разведки)."""
        receiver = created_user()
        outsider = created_user()
        notification = created_notification(users=[receiver["id"]])

        try:
            outsider_session = login(env, outsider["email"], outsider["password"])
        except LoginError as exc:
            pytest.skip(f"Не удалось залогиниться под сторонним пользователем: {exc}")

        outsider_client = ApiClient(
            session=outsider_session, base_url=env.api_base_url, cookie_name=env.cookie_name
        )
        resp = outsider_client.get(f"/notifications/{notification['id']}")
        assert resp.status_code in (403, 404), f"Ожидали 403/404, получили {resp.status_code}: {resp.text}"

    @allure.title("GET /notifications/{id} для несуществующего id → 404")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.notifications
    def test_get_nonexistent_notification_returns_404(self, api_client):
        """Кандидат в дефект (не проверяется assert-ом, только фиксируется в отчёте задачи):
        тело 404-ответа содержит полный стек-трейс Laravel-исключения — утечка деталей
        реализации наружу (см. README §13)."""
        resp = api_client.get("/notifications/999999999")
        assert resp.status_code == 404, f"Ожидали 404, получили {resp.status_code}: {resp.text}"
