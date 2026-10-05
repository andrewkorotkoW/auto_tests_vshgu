"""Юнит-тесты test_data_generation/lib.py: без сети, без --env, без .env/токенов.

Никаких фикстур из корневого conftest.py (api_client/env_session/...) — они требуют
реальной авторизованной сессии. Здесь клиенты либо полностью фейковые (FakeClient/
FakeResponse), либо DryRunClient из самого lib.py, который сокетов не открывает.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.tools

# Тот же способ импорта, что в test_data_generation/generate.py: репозиторий и сама
# папка test_data_generation на sys.path, потому что lib.py и scenarios/*.py делают
# "from lib import ..." (без префикса test_data_generation.), а не пакетный импорт.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_GENERATOR_DIR = os.path.join(_REPO_ROOT, "test_data_generation")
for _path in (_REPO_ROOT, _GENERATOR_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import lib  # noqa: E402
from lib import (  # noqa: E402
    Ctx,
    Manifest,
    ResilientClient,
    _id,
    build_clients,
    is_conflict,
    request_tolerant,
)
from config.environments import Environment  # noqa: E402


class FakeResponse:
    """Минимальный дублёр requests.Response: то, что реально читает lib.py."""

    def __init__(self, status_code: int, payload: dict = None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.text = json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        return self._payload


class FakeClient:
    """Клиент с методом post, отдающий заранее заготовленные ответы по очереди."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def post(self, endpoint, json=None):
        self.calls += 1
        return self._responses.pop(0)


@pytest.fixture
def fake_env():
    """Environment с заведомо нерезолвящимся хостом (.invalid, RFC 2606) — на случай,
    если тест по ошибке всё же попытается сходить в сеть, вызов сразу упадёт по DNS,
    а не тихо достучится до реального стенда."""
    return Environment(
        name="unit-test",
        api_base_url="http://unit-test.invalid/api/v1",
        ui_base_url="http://unit-test.invalid",
        cookie_name="unit-test",
        cookie="",
        global_base_url="http://unit-test.invalid/global/api/v1",
        cas_auth_token="",
        external_system_client_token="",
        lpd_jwt_token="",
    )


# ---------- 1. парсинг id ----------

@pytest.mark.parametrize(
    "body,keys,expected",
    [
        ({"data": {"id": 42}}, (), 42),
        ({"data": {"program_id": 42}}, ("program_id",), 42),
        ({"data": {"stream_id": 7}}, ("stream_id",), 7),
        ({"data": {"user_id": 9}}, ("user_id",), 9),
    ],
)
def test_id_parses_known_keys(body, keys, expected):
    assert _id(FakeResponse(200, body), *keys) == expected


def test_id_prefers_plain_id_over_requested_key():
    """Ключ "id" в приоритете всегда, даже если явно запрошен другой ключ и он тоже есть —
    так и задумано в lib._id (порядок обхода: ("id",) + keys)."""
    resp = FakeResponse(200, {"data": {"id": 1, "program_id": 99}})
    assert _id(resp, "program_id") == 1


def test_id_falls_back_to_top_level_when_data_is_not_a_dict():
    """Внешний CAS API иногда дублирует id на верхнем уровне, а "data" при этом список."""
    resp = FakeResponse(200, {"data": [1, 2, 3], "user_id": 55})
    assert _id(resp, "user_id") == 55


def test_id_raises_when_no_id_present():
    resp = FakeResponse(200, {"data": {"name": "без id"}})
    with pytest.raises(RuntimeError):
        _id(resp)


# ---------- 2. 422 «уже существует» как не-ошибка ----------

def test_is_conflict_true_for_already_exists_422():
    resp = FakeResponse(422, {"message": "Организация уже существует"})
    assert is_conflict(resp) is True


def test_is_conflict_false_for_other_422():
    resp = FakeResponse(422, {"message": "Поле обязательно для заполнения"})
    assert is_conflict(resp) is False


def test_is_conflict_false_when_status_not_in_conflict_statuses():
    resp = FakeResponse(400, {"message": "уже существует"})
    assert is_conflict(resp) is False


def test_request_tolerant_conflict_treated_as_success():
    client = FakeClient([FakeResponse(422, {"message": "Организация уже существует"})])
    resp = request_tolerant(client, "post", "/orgs", json={})
    assert resp.status_code == 422
    assert client.calls == 1


def test_request_tolerant_raises_on_real_error():
    client = FakeClient([FakeResponse(422, {"message": "Поле обязательно для заполнения"})])
    with pytest.raises(RuntimeError):
        request_tolerant(client, "post", "/orgs", json={})


def test_request_tolerant_ok_status_passthrough():
    client = FakeClient([FakeResponse(201, {"data": {"id": 5}})])
    resp = request_tolerant(client, "post", "/orgs", json={})
    assert resp.status_code == 201


# ---------- 3. retry на 5xx ----------

def test_resilient_client_retries_until_success(monkeypatch):
    monkeypatch.setattr(lib.time, "sleep", lambda *_a, **_kw: None)
    client = ResilientClient(
        FakeClient([FakeResponse(500), FakeResponse(200, {"data": {"id": 1}})]),
        retries=2,
        backoff=0,
    )
    resp = client.post("/things", json={})
    assert resp.status_code == 200
    assert client._client.calls == 2


def test_resilient_client_exhausts_retries_and_returns_last_5xx(monkeypatch):
    """ResilientClient сам не бросает исключение — отдаёт последний ответ после исчерпания
    попыток (retries=2 -> 1 первая попытка + 2 повтора = 3 вызова)."""
    monkeypatch.setattr(lib.time, "sleep", lambda *_a, **_kw: None)
    client = ResilientClient(
        FakeClient([FakeResponse(503), FakeResponse(503), FakeResponse(503)]),
        retries=2,
        backoff=0,
    )
    resp = client.post("/things", json={})
    assert resp.status_code == 503
    assert client._client.calls == 3


def test_request_tolerant_raises_after_retries_exhausted(monkeypatch):
    """Комбинация ResilientClient + request_tolerant: если все попытки вернули 5xx,
    итоговая ошибка всё-таки пробрасывается — уже на уровне request_tolerant."""
    monkeypatch.setattr(lib.time, "sleep", lambda *_a, **_kw: None)
    client = ResilientClient(
        FakeClient([FakeResponse(500, {"message": "Внутренняя ошибка"})] * 3),
        retries=2,
        backoff=0,
    )
    with pytest.raises(RuntimeError):
        request_tolerant(client, "post", "/things", json={})
    assert client._client.calls == 3


# ---------- 4. Manifest: round-trip и путь ----------

def test_manifest_save_load_round_trip(tmp_path):
    manifest = Manifest("develop", "users")
    manifest.record("user", 123, "users.delete(123)")
    manifest.record("program", 456, "programs.mass_delete([456])")
    manifest.skip("lpd", "LPD доступен только на stage")

    path = tmp_path / "test_data_generation" / "manifests" / "develop_users_123.json"
    saved_path = manifest.save(path)

    assert saved_path == path
    assert path.exists()

    loaded = Manifest.load(path)
    assert loaded.to_dict() == manifest.to_dict()
    assert loaded.env == "develop"
    assert loaded.scenario == "users"


def test_manifest_load_defaults_when_fields_missing(tmp_path):
    path = tmp_path / "bare.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    manifest = Manifest.load(path)
    assert manifest.env == "develop"
    assert manifest.scenario == "?"
    assert manifest.created == []
    assert manifest.skipped == []


def test_manifest_path_matches_generate_py_convention(tmp_path, monkeypatch):
    """test_data_generation/generate.py формирует путь как
    MANIFESTS_DIR / f"{env.name}_{scenario}_{int(time.time())}.json" — проверяем через
    сам generate.py (а не дублируем формат строкой), просто подменив MANIFESTS_DIR."""
    import generate as generate_module

    monkeypatch.setattr(generate_module, "MANIFESTS_DIR", tmp_path)

    manifest = Manifest("develop", "users")
    manifest.record("user", 1, "note")
    ts = int(time.time())
    path = generate_module.MANIFESTS_DIR / f"{manifest.env}_{manifest.scenario}_{ts}.json"
    manifest.save(path)

    assert path.parent == tmp_path
    assert path.name == f"develop_users_{ts}.json"
    assert path.exists()


# ---------- 5. dry-run: ни одного сетевого вызова ----------

def test_build_clients_dry_run_never_opens_a_session(fake_env, monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError("dry-run не должен трогать requests.Session")

    monkeypatch.setattr(requests.Session, "request", _boom)

    api_client, cas_client, global_client = build_clients(fake_env, dry_run=True)

    for client in (api_client, cas_client, global_client):
        assert isinstance(client, ResilientClient)
        assert client.session is None  # DryRunClient.session, см. lib.py


def test_dry_run_scenario_produces_plan_without_network_calls(fake_env, monkeypatch):
    """Прогон реального сценария (scenarios/users.py) в dry-run: подменяем
    requests.Session.request так, чтобы любой настоящий HTTP-вызов ронял тест, и
    убеждаемся, что сценарий всё равно строит план (манифест) через DryRunClient."""
    def _boom(*_a, **_kw):
        raise AssertionError("dry-run сценарий сделал реальный HTTP-вызов")

    monkeypatch.setattr(requests.Session, "request", _boom)

    from scenarios import users  # noqa: PLC0415 — импорт после sys.path-хака наверху файла

    api_client, cas_client, global_client = build_clients(fake_env, dry_run=True)
    manifest = Manifest(fake_env.name, "users")
    ctx = Ctx(
        env=fake_env,
        api_client=api_client,
        cas_client=cas_client,
        global_client=global_client,
        count=1,
        tenant=None,
        prefix="unit",
        manifest=manifest,
        dry_run=True,
    )

    users.run(ctx)

    assert manifest.created, "dry-run должен вернуть план шагов (созданные записи манифеста)"
    assert len(manifest.created) == len(users.ROLES)
    assert all(entry["entity"] == "user" for entry in manifest.created)
    assert manifest.skipped == []
