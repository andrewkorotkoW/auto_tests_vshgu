"""Фикстуры для tests/api/helpdesk — админка хелпдеска (Laravel Backpack CRUD, не REST API,
см. docs/helpdesk_recon.md и docstring api.endpoints.helpdesk.HelpdeskEndpoint).

Кука сессии develop общая для домена `.d2.devspark.ru` — admin_session/user_session из
корневого conftest.py подходят напрямую, отдельный логин на хелпдеск не нужен.
"""
import pytest

from api.client import ApiClient
from api.endpoints.helpdesk import HelpdeskEndpoint
from api.helpers.data_generator import generate_helpdesk_group_payload, generate_helpdesk_template_payload
from utils.logger import logger

HELPDESK_BASE_URL = "https://helpdesk-develop.d2.devspark.ru"


@pytest.fixture
def helpdesk_client(env, admin_session):
    return ApiClient(session=admin_session, base_url=HELPDESK_BASE_URL, cookie_name=env.cookie_name)


@pytest.fixture
def helpdesk_endpoint(helpdesk_client):
    return HelpdeskEndpoint(helpdesk_client)


@pytest.fixture
def user_helpdesk_endpoint(env, user_session):
    """HelpdeskEndpoint от имени обычного пользователя портала без ролей хелпдеска —
    для негативных проверок доступа."""
    client = ApiClient(session=user_session, base_url=HELPDESK_BASE_URL, cookie_name=env.cookie_name)
    return HelpdeskEndpoint(client)


@pytest.fixture
def created_helpdesk_group(helpdesk_endpoint):
    """Создаёт группу хелпдеска (Автотест_*, фиктивные IMAP/SMTP) и удаляет в teardown,
    даже если тест упал до собственного удаления."""
    group_ids = []

    def _create(**kwargs):
        payload = generate_helpdesk_group_payload(**kwargs)
        resp = helpdesk_endpoint.create_group(payload)
        assert resp.status_code < 400, f"Не удалось создать группу: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_group_by_name(payload["name"])
        assert found is not None and found["id"], f"Созданная группа не найдена: {payload['name']}"
        group_ids.append(found["id"])
        return {"id": found["id"], "payload": payload}

    yield _create

    for group_id in group_ids:
        try:
            helpdesk_endpoint.delete_group(group_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить группу хелпдеска {group_id}: {exc}")


@pytest.fixture
def created_helpdesk_template(helpdesk_endpoint):
    """Создаёт шаблон ответа (Автотест_*) и удаляет в teardown, даже если тест упал."""
    template_ids = []

    def _create(**kwargs):
        payload = generate_helpdesk_template_payload(**kwargs)
        resp = helpdesk_endpoint.create_template(payload)
        assert resp.status_code < 400, f"Не удалось создать шаблон: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_template_by_name(payload["name"])
        assert found is not None and found["id"], f"Созданный шаблон не найден: {payload['name']}"
        template_ids.append(found["id"])
        return {"id": found["id"], "payload": payload}

    yield _create

    for template_id in template_ids:
        try:
            helpdesk_endpoint.delete_template(template_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить шаблон хелпдеска {template_id}: {exc}")
