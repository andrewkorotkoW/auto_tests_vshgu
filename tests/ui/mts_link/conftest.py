"""Фикстуры для UI-тестов интеграции МТС Линк — каркас до разработки
(docs/missions/2026-09-30_tz2026_mts_link.md, docs/test_cases/mts_link/). Все тесты этого
пакета пропускаются автоматически, пока функциональность не подтверждена на ветке — см.
skip_if_mts_link_not_ready и config/environments.py::is_feature_ready("MTS_LINK_READY").

browser/admin_page/user_page/env/api_client — общие фикстуры из корневого conftest.py,
здесь не переопределяются.
"""
import os

import pytest

from api.endpoints.mts_link import MtsLinkEndpoint
from config.environments import is_feature_ready
from ui.pages.admin_tenant_page import AdminTenantPage
from ui.pages.admin_event_mts_page import AdminEventMtsPage
from ui.pages.stream_listeners_page import StreamListenersPage


@pytest.fixture(autouse=True)
def skip_if_mts_link_not_ready():
    """Пропускает все тесты пакета, если флаг MTS_LINK_READY не выставлен в .env (см.
    .env.example) — до появления ветки с реализацией интеграции селекторы
    ui/pages/admin_tenant_page.py, ui/pages/admin_event_mts_page.py,
    ui/pages/stream_listeners_page.py и точечное расширение ui/pages/activity_page.py
    не подтверждены и реальный прогон бессмысленен."""
    if not is_feature_ready("MTS_LINK_READY"):
        pytest.skip("MTS_LINK_READY не выставлен — интеграция МТС Линк ещё не реализована на этом стенде")


@pytest.fixture
def mts_link_endpoint(api_client):
    return MtsLinkEndpoint(api_client)


@pytest.fixture
def mts_link_tenant_id() -> int:
    tenant_id = os.getenv("MTS_LINK_TENANT_ID")
    if not tenant_id:
        pytest.skip("MTS_LINK_TENANT_ID не задан в .env — нет тенанта с интеграцией для теста")
    return int(tenant_id)


@pytest.fixture
def admin_tenant_page(admin_page) -> AdminTenantPage:
    return AdminTenantPage(admin_page)


@pytest.fixture
def admin_event_mts_page(admin_page) -> AdminEventMtsPage:
    return AdminEventMtsPage(admin_page)


@pytest.fixture
def stream_listeners_page(admin_page) -> StreamListenersPage:
    return StreamListenersPage(admin_page)
