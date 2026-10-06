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

HELPDESK_BASE_URL_DEFAULT = "https://helpdesk-develop.d2.devspark.ru"

def _helpdesk_base_url(env) -> str:
    """Хост хелпдеска для текущего стенда: явный HELPDESK_URL, иначе portal-<stand> → helpdesk-<stand>
    (develop → helpdesk-develop.d2.devspark.ru, k8s → helpdesk-k8s-release.v2.gosedu.ru); сессионная
    кука общая для поддомена, отдельный логин не нужен."""
    import os
    explicit = os.getenv("HELPDESK_URL")
    if explicit:
        return explicit.rstrip("/")
    ui = env.ui_base_url.rstrip("/")
    if "://portal-" in ui:
        return ui.replace("://portal-", "://helpdesk-")
    if "://portal." in ui:
        return ui.replace("://portal.", "://helpdesk.")
    return HELPDESK_BASE_URL_DEFAULT



@pytest.fixture
def helpdesk_client(env, admin_session):
    return ApiClient(session=admin_session, base_url=_helpdesk_base_url(env), cookie_name=env.cookie_name)


@pytest.fixture
def helpdesk_endpoint(helpdesk_client):
    return HelpdeskEndpoint(helpdesk_client)


@pytest.fixture
def user_helpdesk_endpoint(env, user_session):
    """HelpdeskEndpoint от имени обычного пользователя портала без ролей хелпдеска —
    для негативных проверок доступа."""
    client = ApiClient(session=user_session, base_url=_helpdesk_base_url(env), cookie_name=env.cookie_name)
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
def helpdesk_existing_group_id(helpdesk_endpoint):
    """ID уже существующей системной группы «Личная группа» — только читается
    (find_group_by_name), не создаётся/не редактируется/не удаляется. Нужна как
    обязательный `group_id` при создании записей 6 из 7 справочников хелпдеска (см.
    api.endpoints.helpdesk._DICT_DEFINITIONS и docstring HelpdeskDictEndpoint: без
    group_id сервер отвечает 422). Своя тестовая группа для этого не подходит —
    GroupCrudController всё ещё падает 500 на успешном создании (см. test_groups_api.py,
    xfail), поэтому справочники ссылаются на уже существующую группу, не мутируя её."""
    found = helpdesk_endpoint.find_group_by_name("Личная группа")
    assert found is not None and found["id"], "Не найдена системная группа «Личная группа» для group_id справочников"
    return found["id"]


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
