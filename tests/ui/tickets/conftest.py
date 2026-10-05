"""Фикстуры для UI-тестов техподдержки (/support).

На develop нет отдельных DEVELOP_USER_LOGIN/DEVELOP_ADMIN_LOGIN, поэтому user_session
(и storage_state роли "user", под которой авторизован user_page) — тот же аккаунт, что
и admin_session (см. README §13). tickets_endpoint здесь под user_session — используется
только для поиска и закрытия обращения, созданного через UI-форму, в teardown теста.
"""
import pytest

from api.client import ApiClient
from api.endpoints.tickets import TicketsEndpoint


@pytest.fixture
def user_api_client(env, user_session):
    return ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)


@pytest.fixture
def tickets_endpoint(user_api_client):
    return TicketsEndpoint(user_api_client)
