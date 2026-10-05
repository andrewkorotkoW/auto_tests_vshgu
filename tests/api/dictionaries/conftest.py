"""Фикстуры для tests/api/dictionaries — единый REST-ресурс /dictionaries (см.
docs/plans/2026-09-25_dictionaries_mission.md и api/endpoints/dictionaries.py).

SAFE_DICTIONARY_TYPES — типы, для которых POST /dictionaries {name, type} (без
дополнительного meta) создаёт полностью рабочий элемент: GET /dictionaries/by-type/{type}
и постраничный список после этого читаются нормально. Round-trip CRUD (create/list/
update/delete) покрывается именно по ним.

`project`/`program_level` сюда намеренно не входят — на develop подтверждён дефект:
POST /dictionaries {name, type: "project"} без meta.experts_entity_id создаёт элемент
(201), но затем ломает GET /dictionaries/by-type/project и постраничный список этого
типа (500 "Undefined array key experts_entity_id" в ExpertsDictionaryMeta.php) для всех
пользователей, пока сломанный элемент не удалить по id напрямую (find_by_name искать
его после этого уже не может — сам использует list_by_type, который тоже падает).
Обнаружено и воспроизведено вручную во время разведки к этой задаче (сломанный элемент
на develop создавался и тут же удалялся по id из ответа create(), без потери данных
стенда) — см. test_dictionaries_negative_api.py::test_create_experts_type_without_meta_breaks_type_reads.

`region`/`municipality` — read-only справочники ФИАС на develop (см. мишн-док),
создавать их тестами не нужно; связь с ними проверяется на уже существующих элементах
через профиль пользователя (test_dictionaries_association_api.py).
"""
import pytest

from api.client import ApiClient
from api.endpoints.dictionaries import DictionariesEndpoint
from api.helpers.data_generator import generate_dictionary_payload
from config.environments import login
from utils.logger import logger

SAFE_DICTIONARY_TYPES = ["program_type", "program_department", "learning_format", "tag"]
EXPERTS_META_DICTIONARY_TYPES = ["project", "program_level"]


@pytest.fixture
def dictionaries_endpoint(api_client):
    return DictionariesEndpoint(api_client)


@pytest.fixture
def second_user_dictionaries_endpoint(env, created_user):
    """DictionariesEndpoint под настоящим вторым пользователем (отдельный логин/пароль,
    отдельная requests.Session, см. tests/api/tickets/conftest.py) — на develop
    admin_session/user_session физически совпадают с одним аккаунтом (README §13),
    поэтому для проверки прав обычного пользователя нужен реально другой аккаунт."""
    user = created_user()
    session = login(env, user["email"], user["password"])
    client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    return DictionariesEndpoint(client)


@pytest.fixture
def created_dictionary_item(dictionaries_endpoint):
    """Создаёт элемент справочника и удаляет его по id в teardown.

    Удаление всегда идёт по id, полученному прямо из ответа create() — не через
    find_by_name/list_by_type, которые для EXPERTS_META_DICTIONARY_TYPES без meta
    могут быть недоступны (см. модуль-докстринг)."""
    created = []

    def _create(dictionary_type: str = "program_type", **kwargs):
        payload = generate_dictionary_payload(dictionary_type=dictionary_type, **kwargs)
        item = dictionaries_endpoint.create(payload["name"], payload["type"])
        created.append(item["id"])
        return item

    yield _create

    for item_id in created:
        try:
            dictionaries_endpoint.delete(item_id)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить элемент справочника {item_id}: {exc}")
