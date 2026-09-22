"""Общие хелперы CLI-генератора тестовых данных (test_data_generation/generate.py).

Клиенты собираются так же, как в conftest.py (фикстуры api_client/env_session):
config.environments.get_session(env) + api.client.ApiClient. Сценарии в
test_data_generation/scenarios/*.py получают все клиенты и общие утилиты через Ctx.
"""
import itertools
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests

from api.client import ApiClient
from config.environments import Environment, get_session
from utils.logger import logger

# Единственное место с паролем по умолчанию для создаваемых тестовых пользователей —
# все сценарии берут его отсюда, а не хардкодят своё значение.
DEFAULT_PASSWORD = "SecurePass123"


def _msg(resp) -> str:
    """Читаемое сообщение об ошибке (сервер экранирует кириллицу в \\uXXXX)."""
    try:
        j = resp.json()
    except ValueError:
        return resp.text[:300]
    parts = [j.get("message")] if j.get("message") else []
    errors = j.get("errors")
    if isinstance(errors, list):
        parts += [str(e) for e in errors]
    elif isinstance(errors, dict):
        parts += [f"{k}: {' '.join(map(str, v))}" for k, v in errors.items()]
    return "; ".join(parts)[:300] or resp.text[:300]


def _id(resp, *keys):
    """ID сущности из ответа: {"data": {"id"|"program_id"|"stream_id"|"user_id": ...}}
    либо тот же набор ключей на верхнем уровне (внешний CAS API их иногда дублирует)."""
    body = resp.json()
    data = body.get("data", body)
    for key in ("id",) + keys:
        if isinstance(data, dict) and data.get(key) is not None:
            return data[key]
    for key in ("id",) + keys:
        if body.get(key) is not None:
            return body[key]
    raise RuntimeError(f"в ответе нет id: {data}")


def is_conflict(resp, substr: str = "уже существует", statuses=(422,)) -> bool:
    """Ответ с кодом из statuses и текстом substr в decoded-теле (не resp.text — сервер
    отдаёт кириллицу в \\uXXXX, поэтому сравнение идёт через _msg()/resp.json(), как в
    generate_cas_data.py: 422 «уже существует» для tenant-org-locations, 400 «должен(а)
    быть не синхронизирован(а)» для повторной синхронизации CAS — в обоих случаях
    сущность/состояние уже есть, это не ошибка сценария."""
    if resp.status_code not in statuses:
        return False
    return substr in _msg(resp)


class DryRunResponse:
    """Response-подобный объект для DryRunClient — тот же интерфейс, что у requests.Response
    (status_code/ok/text/json()), чтобы код api/endpoints/*.py, писанный под настоящие
    ответы requests, работал без изменений и в dry-run."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


class DryRunClient:
    """Замена ApiClient для --dry-run: ни один метод не открывает сокет — вместо
    session.post/get/... только логирование и синтетический ответ с фейковым
    инкрементным id, чтобы сценарии могли строить цепочки (программа -> поток -> ...)
    так же, как при реальном прогоне. Именно отсутствие requests.Session здесь
    (а не мок поверх неё) и есть гарантия «ни одного сетевого вызова»."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self._ids = itertools.count(900000001)

    def _fake_response(self, method: str, endpoint: str, payload=None) -> DryRunResponse:
        logger.info(f"[dry-run] был бы {method} {self.base_url}{endpoint} json={payload}")
        fake_id = next(self._ids)
        attrs = {}
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict) and isinstance(data.get("attributes"), dict):
                attrs = dict(data["attributes"])
            elif "data" not in payload:
                attrs = {k: v for k, v in payload.items() if isinstance(k, str)}
        attrs.setdefault("id", fake_id)
        attrs.setdefault("content_id", fake_id)
        attrs.setdefault("name", attrs.get("name", f"dry-run-{fake_id}"))
        id_aliases = {
            "id": fake_id,
            "program_id": fake_id,
            "stream_id": fake_id,
            "user_id": fake_id,
            "template_id": fake_id,
            "content_id": fake_id,
        }
        body = {
            "data": {"attributes": attrs, **id_aliases},
            **id_aliases,
        }
        return DryRunResponse(200, body)

    def post(self, endpoint: str, json: dict = None) -> DryRunResponse:
        return self._fake_response("POST", endpoint, json)

    def put(self, endpoint: str, json: dict = None) -> DryRunResponse:
        return self._fake_response("PUT", endpoint, json)

    def patch(self, endpoint: str, json: dict = None) -> DryRunResponse:
        return self._fake_response("PATCH", endpoint, json)

    def get(self, endpoint: str, headers: dict = None) -> DryRunResponse:
        return self._fake_response("GET", endpoint, None)

    def delete(self, endpoint: str, json: dict = None) -> DryRunResponse:
        return self._fake_response("DELETE", endpoint, json)

    def upload(self, endpoint: str, files: dict, data: dict = None) -> DryRunResponse:
        return self._fake_response("UPLOAD", endpoint, data)


class ResilientClient:
    """Оборачивает ApiClient/DryRunClient: retry на 5xx (сеть иногда отвечает 502/503
    под нагрузкой на develop), 2 повтора сверх первой попытки с короткой паузой.
    Все прочие атрибуты (session, base_url — их использует, например,
    TincanEndpoint.upload_certificate_file) прозрачно проксируются на обёрнутый клиент."""

    def __init__(self, client, retries: int = 2, backoff: float = 0.5):
        self._client = client
        self._retries = retries
        self._backoff = backoff

    def __getattr__(self, name):
        return getattr(self._client, name)

    def _with_retry(self, method_name: str, *args, **kwargs):
        attempt = 0
        while True:
            resp = getattr(self._client, method_name)(*args, **kwargs)
            if resp.status_code < 500 or attempt >= self._retries:
                return resp
            attempt += 1
            logger.warning(
                f"{method_name.upper()} вернул {resp.status_code}, повтор {attempt}/{self._retries}..."
            )
            time.sleep(self._backoff * attempt)

    def post(self, *args, **kwargs):
        return self._with_retry("post", *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._with_retry("put", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._with_retry("patch", *args, **kwargs)

    def get(self, *args, **kwargs):
        return self._with_retry("get", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._with_retry("delete", *args, **kwargs)

    def upload(self, *args, **kwargs):
        return self._with_retry("upload", *args, **kwargs)


def request_tolerant(client, method: str, endpoint: str, json: dict = None,
                      ok_statuses=(200, 201), conflict_substr: str = "уже существует",
                      conflict_statuses=(422,)):
    """Обёртка для прямых POST/PUT-вызовов, для которых ещё нет метода в api/endpoints/*
    (или для которых есть метод, но его собственная проверка «это не ошибка» сравнивает
    с resp.text, а не с decoded-телом, и поэтому не срабатывает на escaped-кириллице):
    успех — ok_statuses, конфликт (см. is_conflict) — тоже успех, иначе RuntimeError
    с читаемым сообщением. Retry на 5xx уже сделан в ResilientClient, если client им обёрнут."""
    resp = getattr(client, method)(endpoint, json=json)
    if resp.status_code in ok_statuses:
        return resp
    if is_conflict(resp, conflict_substr, statuses=conflict_statuses):
        logger.info(f"{method.upper()} {endpoint}: {conflict_substr} — считаем успехом")
        return resp
    raise RuntimeError(f"{method.upper()} {endpoint} -> {resp.status_code}: {_msg(resp)}")


class Manifest:
    """Список созданных сценарием сущностей — для --cleanup и для финального отчёта.
    JSON: {"env":.., "scenario":.., "created": [{"entity":.., "id":.., "how_to_delete":..}]}.
    """

    def __init__(self, env: str, scenario: str):
        self.env = env
        self.scenario = scenario
        self.created: list[dict] = []
        self.skipped: list[dict] = []

    def record(self, entity: str, id_, note: str) -> None:
        self.created.append({"entity": entity, "id": id_, "how_to_delete": note})
        logger.info(f"  + {entity} id={id_} ({note})")

    def skip(self, entity: str, reason: str) -> None:
        """Шаг сознательно не выполнен (нет API-пути / нет модуля на окружении /
        LPD доступен только на stage и т.п.) — не создаёт сущность для удаления,
        но должен быть виден и в логе, и в итоговом отчёте/манифесте."""
        self.skipped.append({"entity": entity, "reason": reason})
        logger.info(f"  - {entity} пропущено: {reason}")

    def to_dict(self) -> dict:
        return {"env": self.env, "scenario": self.scenario, "created": self.created, "skipped": self.skipped}

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path) -> "Manifest":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        manifest = cls(data.get("env", "develop"), data.get("scenario", "?"))
        manifest.created = data.get("created", [])
        manifest.skipped = data.get("skipped", [])
        return manifest


@dataclass
class Ctx:
    """Контекст, который получает каждый сценарий: env, готовые клиенты, параметры
    запуска (count/tenant/prefix), манифест для записи созданного, флаг dry-run."""

    env: Environment
    api_client: Any
    cas_client: Any
    global_client: Any
    count: int
    tenant: Optional[int]
    prefix: Optional[str]
    manifest: Manifest
    dry_run: bool
    _ts: int = field(default_factory=lambda: int(time.time()))

    def name(self, tag: str = "") -> str:
        """Имя сущности: 'Автотест_<prefix>_<ts>[_<tag>]', либо без prefix — 'Автотест_<ts>[_<tag>]'."""
        base = f"Автотест_{self.prefix}_{self._ts}" if self.prefix else f"Автотест_{self._ts}"
        return f"{base}_{tag}" if tag else base

    def dry_or(self, description: str, fake, real_fn):
        """Для шагов, которые не проходят через api_client (login по логину/паролю,
        upload_certificate_file через curl) — в dry-run они не должны вызываться
        вообще, поэтому real_fn выполняется только если dry_run=False."""
        if self.dry_run:
            logger.info(f"[dry-run] был бы {description}")
            return fake
        return real_fn()


def build_clients(env: Environment, dry_run: bool = False):
    """Собирает клиентов ровно как conftest.py (api_client/env_session,
    external_cas_endpoint, api_client_global), но:
    - в dry-run вместо ApiClient подставляется DryRunClient (никаких запросов вообще);
    - в реальном режиме каждый клиент обёрнут ResilientClient (retry на 5xx).
    Возвращает (api_client, cas_client, global_client).
    """
    if dry_run:
        return (
            ResilientClient(DryRunClient(env.api_base_url)),
            ResilientClient(DryRunClient(env.api_base_url)),
            ResilientClient(DryRunClient(env.global_base_url)),
        )

    session = get_session(env)
    api_client = ResilientClient(ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name))

    cas_session = requests.Session()
    cas_session.cookies.update(session.cookies)
    cas_session.headers["Authorization"] = env.cas_auth_token
    cas_session.headers["Accept"] = "application/json"
    cas_session.headers["Content-Type"] = "application/json"
    cas_client = ResilientClient(ApiClient(session=cas_session, base_url=env.api_base_url))

    global_client = ResilientClient(
        ApiClient(session=session, base_url=env.global_base_url, cookie_name=env.cookie_name)
    )
    return api_client, cas_client, global_client
