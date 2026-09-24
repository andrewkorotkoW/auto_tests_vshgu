"""Фикстуры для tests/api/tickets — обращения в техподдержку (/api/v1/tickets/*).

На develop нет отдельных DEVELOP_USER_LOGIN/DEVELOP_ADMIN_LOGIN, поэтому
user_session/admin_session из корневого conftest.py совпадают с одним аккаунтом
(см. README §13). Для сценариев «чужое обращение» нужен второй, по-настоящему
другой пользователь — second_user_tickets_endpoint логинится под ним отдельно
через config.environments.login (UsersEndpoint.create + пароль из payload).
"""
import pytest

from api.client import ApiClient
from api.endpoints.tickets import TicketsEndpoint
from api.helpers.data_generator import generate_ticket_payload
from config.environments import login
from utils.logger import logger


@pytest.fixture
def user_api_client(env, user_session):
    return ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)


@pytest.fixture
def tickets_endpoint(user_api_client):
    return TicketsEndpoint(user_api_client)


@pytest.fixture
def created_ticket(tickets_endpoint):
    """Создаёт обращение через POST /tickets (payload с префиксом 'Автотест_') и находит
    его по теме в my-tickets — сам create не возвращает id (см. TicketsEndpoint.find_by_title).
    Закрывает обращение в teardown, даже если тест упал."""
    ticket_ids = []

    def _create(**kwargs):
        payload = generate_ticket_payload(**kwargs)
        tickets_endpoint.create(payload)
        ticket = tickets_endpoint.find_by_title(payload["title"])
        assert ticket is not None, f"Созданное обращение не найдено в my-tickets: {payload['title']}"
        ticket_ids.append(ticket["id"])
        return ticket

    yield _create

    for ticket_id in ticket_ids:
        try:
            tickets_endpoint.close(ticket_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось закрыть обращение {ticket_id} в teardown: {exc}")


@pytest.fixture
def second_user_tickets_endpoint(env, created_user):
    """TicketsEndpoint под настоящим вторым пользователем (отдельный логин/пароль,
    отдельная requests.Session) — для проверок доступа к чужому обращению."""
    user = created_user()
    session = login(env, user["email"], user["password"])
    client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    return TicketsEndpoint(client)
