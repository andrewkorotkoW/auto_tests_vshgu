"""Фикстуры для API-тестов уведомлений (/api/v1/notifications/*).

created_notification/created_template создают данные с префиксом 'Автотест_'
(api.helpers.data_generator) и best-effort подчищают их в teardown — удаление
на develop асинхронное и не всегда успевает подтвердиться (см. README §13 и
xfail в test_notifications_crud_api.py / templates/test_notification_templates_api.py),
поэтому teardown не падает, если удаление ещё не применилось.
"""
import allure
import pytest

from api.client import ApiClient
from api.endpoints.notifications import NotificationsEndpoint
from api.helpers.data_generator import generate_notification_payload, generate_notification_template_payload
from utils.logger import logger


@pytest.fixture
def notifications_endpoint(api_client):
    return NotificationsEndpoint(api_client)


@pytest.fixture
def user_notifications_endpoint(env, user_session):
    """NotificationsEndpoint от имени фикстуры user_session.

    На develop admin_session и user_session физически один и тот же аккаунт — в .env нет
    отдельных DEVELOP_USER_LOGIN/DEVELOP_USER_PASSWORD, обе роли фолбэк-ятся на общий
    DEVELOP_LOGIN (см. README §13). Тест, использующий эту фикстуру, поэтому не проверяет
    реальную изоляцию «слушатель видит только своё», а только то, что GET /notifications
    доступен под сессией роли user и содержит уведомление, созданное под admin_session.
    """
    client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    return NotificationsEndpoint(client)


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


@pytest.fixture
def created_template(notifications_endpoint):
    template_ids = []

    def _create(**kwargs):
        payload = generate_notification_template_payload(**kwargs)
        with allure.step(f"Создать шаблон уведомления '{payload['name']}'"):
            data = notifications_endpoint.create_template(payload)
        template_ids.append(data["id"])
        return data

    yield _create

    for template_id in template_ids:
        try:
            notifications_endpoint.delete_templates([template_id])
        except Exception as exc:
            logger.warning(f"Failed to delete template {template_id}: {exc}")
