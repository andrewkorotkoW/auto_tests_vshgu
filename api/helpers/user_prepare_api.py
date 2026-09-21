"""Подготовка пользователя к UI-тестам через API: логин, согласие на обработку
персональных данных, закрытие онбординг-историй — чтобы UI-тест не тратил время
на прохождение этих шагов вручную через форму.

Перенос tests/api/helpers/user_prepare_api.py коллеги (репозиторий lms,
feature/my-tests) под наш ApiClient/config.environments.login и
api.helpers.expectations.expect_status вместо голых assert/raise.
"""
from typing import Iterable, Optional

import requests

from api.client import ApiClient
from api.endpoints.onboarding import OnboardingEndpoint
from api.helpers.expectations import expect_status
from config.environments import Environment, login


def login_user_session(env: Environment, login_: str, password: str) -> requests.Session:
    """Логинится под пользователем login_/password так же, как это делает браузер
    (CSRF-токен со страницы логина + форма /auth/login)."""
    return login(env, login_, password)


def accept_personal_data_agreement(client: ApiClient) -> None:
    """PUT /me/update — принять согласие на обработку персональных данных."""
    resp = client.put("/me/update", json={"data": {"attributes": {"agreement": True}}})
    expect_status(resp, (200, 201, 204))


def complete_onboarding_stories(client: ApiClient, stories: Optional[Iterable[str]] = None) -> None:
    """Закрыть список историй онбординга (по умолчанию — OnboardingEndpoint.DEFAULT_STORIES)."""
    OnboardingEndpoint(client).complete_all(stories)


def prepare_user_for_tests_via_api(
    env: Environment,
    login_: str,
    password: str,
    onboarding_stories: Optional[Iterable[str]] = None,
) -> None:
    """Готовит пользователя к UI-тестам: логин под ним, согласие на ПД,
    закрытие онбординг-историй. Используется перед UI-сценариями, которые
    не являются тестом самого онбординга/анкеты (иначе эти шаги проходят
    в UI намеренно, см. ui/pages/onboarding_page.py)."""
    session = login_user_session(env, login_, password)
    client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)

    accept_personal_data_agreement(client)
    complete_onboarding_stories(client, onboarding_stories)
