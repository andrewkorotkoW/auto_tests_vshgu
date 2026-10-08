"""Юнит-тесты сборки окружений в config/environments.py: без сети, без --env.

До этой задачи сборка самих окружений (_build_environment/ENVIRONMENTS) тестами не была
покрыта вообще — tests/tools/test_lib.py импортирует только dataclass Environment как
дублёр для тестов test_data_generation/lib.py. Здесь — пункт 4 плана
docs/plans/2026-10-07_ci_pipeline_mission.md: окружение "stand" (универсальный STAND_*
профиль для CI других ЦОДов, см. docs/DEVOPS.md раздел 4.1), которое добавил michael.

Каждый тест сам выставляет нужные STAND_* переменные через monkeypatch.setenv и
перезагружает config.environments, чтобы ENVIRONMENTS/"stand" пересобралась с ними —
модуль строит ENVIRONMENTS на уровне импорта, поэтому иначе переменные не подхватятся.
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import config.environments as environments_module

pytestmark = pytest.mark.tools

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Все переменные, которые читает окружение "stand" — чтобы гарантированно стирать их перед
# каждым тестом (на случай, если что-то всё же просочилось из процесса/.env) и не зависеть
# от порядка тестов в файле.
_ALL_STAND_VARS = [
    "STAND_URL",
    "STAND_COOKIE_NAME",
    "STAND_ADMIN_LOGIN",
    "STAND_ADMIN_PASSWORD",
    "STAND_USER_LOGIN",
    "STAND_USER_PASSWORD",
    "STAND_API_URL",
    "STAND_GLOBAL_URL",
    "STAND_CAS_TOKEN",
    "STAND_EXTERNAL_TOKEN",
    "STAND_LPD_JWT",
    "STAND_BUK_TOKEN",
    "HELPDESK_URL",
]


@pytest.fixture
def stand_env(monkeypatch):
    """Чистит все STAND_*/HELPDESK_URL, даёт monkeypatch.setenv тесту, а по завершении
    теста восстанавливает config.environments к состоянию «как при обычном импорте»:
    сначала monkeypatch.undo() (снимает переменные), потом reload — иначе финальный reload
    в teardown подхватил бы ещё не отменённые monkeypatch-переменные."""
    for name in _ALL_STAND_VARS:
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch
    monkeypatch.undo()
    importlib.reload(environments_module)


# ---------- 1. обязательные переменные: cookie_name и учётки ----------

def test_stand_environment_built_from_explicit_env_vars(stand_env):
    stand_env.setenv("STAND_URL", "https://portal-mystand.example.com")
    stand_env.setenv("STAND_COOKIE_NAME", "mystand_session")
    stand_env.setenv("STAND_ADMIN_LOGIN", "admin@mystand")
    stand_env.setenv("STAND_ADMIN_PASSWORD", "admin-pass")
    stand_env.setenv("STAND_USER_LOGIN", "user@mystand")
    stand_env.setenv("STAND_USER_PASSWORD", "user-pass")

    importlib.reload(environments_module)

    env = environments_module.ENVIRONMENTS["stand"]
    assert env.name == "stand"
    assert env.cookie_name == "mystand_session"
    assert env.ui_base_url == "https://portal-mystand.example.com"
    assert environments_module.get_credentials("stand", "admin") == ("admin@mystand", "admin-pass")
    assert environments_module.get_credentials("stand", "user") == ("user@mystand", "user-pass")


# ---------- 2. вывод api/global из STAND_URL, явные STAND_API_URL/STAND_GLOBAL_URL в приоритете ----------

def test_stand_api_and_global_urls_derived_from_stand_url(stand_env):
    stand_env.setenv("STAND_URL", "https://portal-mystand.example.com")

    importlib.reload(environments_module)

    env = environments_module.ENVIRONMENTS["stand"]
    assert env.api_base_url == "https://portal-mystand.example.com/api/v1"
    assert env.global_base_url == "https://global-mystand.example.com/api/v1"


def test_stand_explicit_api_and_global_urls_override_derived(stand_env):
    stand_env.setenv("STAND_URL", "https://portal-mystand.example.com")
    stand_env.setenv("STAND_API_URL", "https://api.custom.example.com/v1")
    stand_env.setenv("STAND_GLOBAL_URL", "https://global.custom.example.com/v1")

    importlib.reload(environments_module)

    env = environments_module.ENVIRONMENTS["stand"]
    assert env.api_base_url == "https://api.custom.example.com/v1"
    assert env.global_base_url == "https://global.custom.example.com/v1"


# ---------- 3. пустые токены интеграций не ломают сборку ----------

def test_stand_integration_tokens_default_to_empty_string(stand_env):
    stand_env.setenv("STAND_URL", "https://portal-mystand.example.com")
    # STAND_CAS_TOKEN/STAND_EXTERNAL_TOKEN/STAND_LPD_JWT/STAND_BUK_TOKEN умышленно не заданы.

    importlib.reload(environments_module)

    env = environments_module.ENVIRONMENTS["stand"]
    assert env.cas_auth_token == ""
    assert env.external_system_client_token == ""
    assert env.lpd_jwt_token == ""
    assert env.buk_token == ""


def test_stand_without_stand_url_has_empty_addresses_not_a_crash(stand_env):
    """Без STAND_URL (и без K8S-подобного хардкод-фолбэка — см. комментарий в
    config/environments.py перед ENVIRONMENTS["stand"]) сборка не падает, адреса пустые."""
    importlib.reload(environments_module)

    env = environments_module.ENVIRONMENTS["stand"]
    assert env.ui_base_url == ""
    assert env.api_base_url == "/api/v1"
    assert env.global_base_url == "/api/v1"


# ---------- 4. HELPDESK_URL: вывод portal- -> helpdesk- для стенда "stand" тоже, явный приоритетнее ----------

def _load_helpdesk_base_url_fn(conftest_path: Path, module_name: str):
    """conftest.py нельзя импортировать как обычный модуль по имени "conftest" — в
    репозитории их много (tests/<feature>/conftest.py), сталкиваются в sys.modules (см.
    feedback_conftest_bare_import_self_collision). Поэтому грузим по пути под уникальным
    псевдонимом, не трогая sys.modules["conftest"]."""
    spec = importlib.util.spec_from_file_location(module_name, conftest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._helpdesk_base_url


@pytest.mark.parametrize(
    "conftest_path,module_name",
    [
        (_REPO_ROOT / "tests" / "api" / "helpdesk" / "conftest.py", "_test_helpdesk_api_conftest"),
        (_REPO_ROOT / "tests" / "ui" / "helpdesk" / "admin" / "conftest.py", "_test_helpdesk_ui_conftest"),
    ],
)
def test_helpdesk_base_url_derived_from_stand_portal_host(conftest_path, module_name, monkeypatch):
    monkeypatch.delenv("HELPDESK_URL", raising=False)
    helpdesk_base_url = _load_helpdesk_base_url_fn(conftest_path, module_name)

    stand_env = SimpleNamespace(name="stand", ui_base_url="https://portal-mystand.example.com")

    assert helpdesk_base_url(stand_env) == "https://helpdesk-mystand.example.com"


@pytest.mark.parametrize(
    "conftest_path,module_name",
    [
        (_REPO_ROOT / "tests" / "api" / "helpdesk" / "conftest.py", "_test_helpdesk_api_conftest_override"),
        (_REPO_ROOT / "tests" / "ui" / "helpdesk" / "admin" / "conftest.py", "_test_helpdesk_ui_conftest_override"),
    ],
)
def test_helpdesk_base_url_explicit_env_var_overrides_derived(conftest_path, module_name, monkeypatch):
    monkeypatch.setenv("HELPDESK_URL", "https://helpdesk.custom.example.com/")
    helpdesk_base_url = _load_helpdesk_base_url_fn(conftest_path, module_name)

    stand_env = SimpleNamespace(name="stand", ui_base_url="https://portal-mystand.example.com")

    assert helpdesk_base_url(stand_env) == "https://helpdesk.custom.example.com"


# ---------- 5. --env stand принимается pytest_addoption (choices=list(ENVIRONMENTS.keys())) ----------

def test_env_stand_accepted_by_pytest_addoption(monkeypatch):
    env = {
        **os.environ,
        "STAND_URL": "https://portal-mystand.example.com",
        "STAND_COOKIE_NAME": "mystand_session",
        "STAND_ADMIN_LOGIN": "admin@mystand",
        "STAND_ADMIN_PASSWORD": "admin-pass",
        "STAND_USER_LOGIN": "user@mystand",
        "STAND_USER_PASSWORD": "user-pass",
    }
    cmd = [
        sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=",
        "--env", "stand",
        str(Path(__file__)),
    ]
    proc = subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True, env=env, timeout=120)

    assert proc.returncode == 0, (
        f"pytest --collect-only --env stand упал (код {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
    )
    assert "invalid choice" not in proc.stderr.lower()
