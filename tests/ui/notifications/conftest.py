"""Фикстуры для UI-тестов уведомлений (/portal-notifications, /admin/notifications).

current_user_id — id аккаунта, под которым авторизованы user_page/admin_page (общий
аккаунт на develop, см. README §13, tests/api/tickets/conftest.py) — определяется через
GET /auth/me, а не хардкодится, чтобы адресовать уведомление получателю без завязки на
конкретный id стенда.

created_notification — как в tests/api/notifications/conftest.py: создаёт уведомление с
префиксом 'Автотест_' и best-effort удаляет его в teardown (удаление на develop
асинхронное, см. README §13).
"""
import allure
import pytest

from api.endpoints.notifications import NotificationsEndpoint
from api.helpers.data_generator import generate_notification_payload
from api.helpers.expectations import expect_status
from utils.logger import logger


@pytest.fixture
def notifications_endpoint(api_client):
    return NotificationsEndpoint(api_client)


@pytest.fixture
def current_user_id(api_client):
    resp = api_client.get("/auth/me")
    expect_status(resp, 200)
    return resp.json()["data"]["id"]


@pytest.fixture
def created_notification(notifications_endpoint):
    notification_ids = []

    def _create(**kwargs):
        payload = generate_notification_payload(**kwargs)
        with allure.step(f"Создать уведомление '{payload['name']}'"):
            data = notifications_endpoint.create(payload)
        notification_ids.append(data["id"])
        return data

    yield _create

    for notification_id in notification_ids:
        try:
            notifications_endpoint.delete([notification_id])
        except Exception as exc:
            logger.warning(f"Failed to delete notification {notification_id}: {exc}")
