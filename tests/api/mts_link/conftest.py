"""Фикстуры для API-тестов интеграции МТС Линк — каркас до разработки
(docs/missions/2026-09-30_tz2026_mts_link.md, docs/test_cases/mts_link/). Все тесты этого
пакета пропускаются автоматически, пока функциональность не подтверждена на ветке — см.
skip_if_mts_link_not_ready и config/environments.py::is_feature_ready("MTS_LINK_READY").

api_client/created_schedule_item/created_program/created_stream/created_module/created_user —
общие фикстуры из корневого conftest.py, здесь не переопределяются.
"""
import os

import pytest

from api.endpoints.mts_link import MtsLinkEndpoint
from config.environments import is_feature_ready


@pytest.fixture(autouse=True)
def skip_if_mts_link_not_ready():
    """Пропускает все тесты пакета, если флаг MTS_LINK_READY не выставлен в .env (см.
    .env.example) — до появления ветки с реализацией интеграции контракт
    api/endpoints/mts_link.py не подтверждён и реальный прогон бессмысленен."""
    if not is_feature_ready("MTS_LINK_READY"):
        pytest.skip("MTS_LINK_READY не выставлен — интеграция МТС Линк ещё не реализована на этом стенде")


@pytest.fixture
def mts_link_endpoint(api_client):
    return MtsLinkEndpoint(api_client)


@pytest.fixture
def mts_link_tenant_id() -> int:
    """Id тенанта с настроенной и проверенной интеграцией МТС Линк — см. MTS_LINK_TENANT_ID
    в .env.example (план, п.4)."""
    tenant_id = os.getenv("MTS_LINK_TENANT_ID")
    if not tenant_id:
        pytest.skip("MTS_LINK_TENANT_ID не задан в .env — нет тенанта с интеграцией для теста")
    return int(tenant_id)
