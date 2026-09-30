"""Фикстуры для API-тестов взаимопроверки ПЗ (p2p) — каркас до разработки
(докs/missions/2026-09-30_tz2026_p2p.md, docs/test_cases/p2p/). Все тесты этого пакета
пропускаются автоматически, пока функциональность не подтверждена на ветке — см.
skip_if_p2p_not_ready и config/environments.py::is_feature_ready("P2P_READY").
"""
import pytest

from api.client import ApiClient
from api.endpoints.p2p import P2PEndpoint
from api.helpers.expectations import expect_status
from config.environments import is_feature_ready, login
from utils.logger import logger


@pytest.fixture(autouse=True)
def skip_if_p2p_not_ready():
    """Пропускает все тесты пакета, если флаг P2P_READY не выставлен в .env (см.
    .env.example) — до появления ветки с реализацией взаимопроверки ПЗ контракт
    api/endpoints/p2p.py не подтверждён и реальный прогон бессмысленен."""
    if not is_feature_ready("P2P_READY"):
        pytest.skip("P2P_READY не выставлен — взаимопроверка ПЗ ещё не реализована на этом стенде")


@pytest.fixture
def p2p_endpoint(api_client):
    return P2PEndpoint(api_client)


@pytest.fixture
def p2p_client_for(env):
    """Фабрика: (ApiClient, P2PEndpoint) под конкретным пользователем (email/password) —
    для многоролевых сценариев p2p (слушатель-автор, слушатель-проверяющий, администратор
    без назначения проверяющим), по аналогии с
    tests/api/dictionaries/conftest.py::second_user_dictionaries_endpoint."""

    def _make(user: dict):
        session = login(env, user["email"], user["password"])
        client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        return client, P2PEndpoint(client)

    return _make


def _submit_answer_as(p2p_client_for, user: dict, homework_id: int, text: str) -> int:
    """Отправляет ответ по ПЗ от имени конкретного пользователя предполагаемым
    POST /homework/{id}/answers (контракт не подтверждён — см. submitted_work) и
    возвращает id созданного ответа (work_id)."""
    client, _ = p2p_client_for(user)
    resp = client.post(f"/homework/{homework_id}/answers", json={"data": {"attributes": {"text": text}}})
    expect_status(resp, (200, 201))
    work_id = resp.json()["data"]["id"]
    logger.info(f"Homework {homework_id}: work {work_id} submitted by {user['id']}")
    return work_id


@pytest.fixture
def submitted_work(created_homework, assigned_user, p2p_endpoint, p2p_client_for):
    """Готовит P2P-ПЗ, слушателя-автора и его сданную работу — общая подготовка для
    тестов peer-проверки/распределения/агрегации/итога/статусов.

    Контракт не подтверждён: предполагается, что «работа» (work_id из
    api/endpoints/p2p.py) — это тот же content answer, что и в обычном ПЗ
    (api/endpoints/homework.py::examine работает с homework/{id}/answers/{answer_id}),
    поэтому ответ отправляется предполагаемым POST /homework/{id}/answers, а не через UI."""

    def _create(**homework_kwargs):
        assigned = assigned_user()
        author = assigned["user"]
        stream = assigned["stream"]
        homework = created_homework(**homework_kwargs)
        p2p_endpoint.enable_peer_review(homework["id"])

        work_id = _submit_answer_as(
            p2p_client_for, author, homework["id"], "Автотест: ответ слушателя для взаимопроверки"
        )

        return {"author": author, "stream": stream, "homework": homework, "work_id": work_id}

    return _create


@pytest.fixture
def stream_with_submitted_works(created_stream, created_homework, created_user, assignments_endpoint,
                                 p2p_endpoint, p2p_client_for):
    """Готовит P2P-ПЗ в потоке с несколькими слушателями, каждый из которых сдал
    собственную работу — общая подготовка для тестов распределения (все работы
    в одном потоке, чтобы можно было распределять их друг другу)."""

    def _create(listeners_count: int = 3, **homework_kwargs):
        stream = created_stream()
        homework = created_homework(**homework_kwargs)
        p2p_endpoint.enable_peer_review(homework["id"])

        listeners = [created_user() for _ in range(listeners_count)]
        assignments_endpoint.assign(stream["program_id"], stream["id"], [u["id"] for u in listeners])

        works = []
        for listener in listeners:
            work_id = _submit_answer_as(
                p2p_client_for, listener, homework["id"],
                f"Автотест: ответ слушателя {listener['id']} для взаимопроверки",
            )
            works.append({"author": listener, "work_id": work_id})

        return {"stream": stream, "homework": homework, "listeners": listeners, "works": works}

    return _create
