"""Фикстуры для UI-тестов интеграции МТС Линк.

Ветка mts-link-release-main тестируется на РЕАЛЬНОМ прод-аккаунте МТС Линк — отдельного
тестового аккаунта нет и не будет (см. docs/test_cases/mts_link/16_prod_safe_run.md).
Поэтому все тесты этого пакета остаются за флагом MTS_LINK_READY (см.
skip_if_mts_link_not_ready и config/environments.py::is_feature_ready) — не только пока
функциональность не подтверждена (как было раньше), но и сознательно: тест, который
реально создаёт МТС-вебинар через UI (test_create_webinar_via_ui.py), не должен
запускаться в обычном полном прогоне/CI, только по явному флагу.

Подтверждено живой разведкой на стенде mts-link-release-main 29.10.2026:
ui/pages/admin_event_mts_page.py (блок создания мероприятия) и
ui/pages/admin_tenant_page.py (вкладка «МТС Линк» в организации) — РЕАЛЬНЫЕ, не
догадки. Их докстринги описывают, что именно подтверждено, а что нет (часть 7/8
карточки статусов в admin_event_mts_page.py всё ещё не разведана).
ui/pages/stream_listeners_page.py и api/endpoints/mts_link.py (кроме схожести с
schedule_items.py по форме) остаются НЕ подтверждены этой разведкой — в этот раз не
тронуты.

browser/admin_page/user_page/env/api_client — общие фикстуры из корневого conftest.py,
здесь не переопределяются.
"""
import os

import allure
import pytest

from api.endpoints.mts_link import MtsLinkEndpoint
from config.environments import is_feature_ready
from ui.pages.admin_tenant_page import AdminTenantPage
from ui.pages.admin_programs_page import AdminProgramsPage
from ui.pages.admin_event_mts_page import AdminEventMtsPage
from ui.pages.stream_listeners_page import StreamListenersPage
from utils.logger import logger


@pytest.fixture(autouse=True)
def skip_if_mts_link_not_ready():
    """Пропускает все тесты пакета, если флаг MTS_LINK_READY не выставлен в .env (см.
    .env.example). Намеренно: часть тестов этого пакета реально создаёт данные (в т.ч.
    мероприятие МТС Линк) на единственном прод-аккаунте МТС Линк — запуск должен быть
    явным выбором, не частью обычного полного прогона/CI."""
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
def admin_programs_page(admin_page) -> AdminProgramsPage:
    return AdminProgramsPage(admin_page)


@pytest.fixture
def admin_event_mts_page(admin_page) -> AdminEventMtsPage:
    return AdminEventMtsPage(admin_page)


@pytest.fixture
def stream_listeners_page(admin_page) -> StreamListenersPage:
    return StreamListenersPage(admin_page)


@pytest.fixture
def register_mts_link_program(programs_endpoint):
    """Регистрирует программы, созданные через UI в тестах этого пакета, для best-effort
    cleanup — как register_practical_program в tests/ui/practical_tasks/conftest.py
    (своя копия: фикстуры conftest.py одного пакета не видны другому)."""
    program_ids = []

    def _register(program_id: int) -> None:
        program_ids.append(program_id)

    yield _register

    if program_ids:
        try:
            programs_endpoint.mass_delete(program_ids)
        except Exception as exc:  # noqa: BLE001 - cleanup не должен скрывать исходный фейл
            allure.attach(
                str(exc),
                name="mts_link_program_cleanup_error",
                attachment_type=allure.attachment_type.TEXT,
            )
            logger.warning(f"Failed to delete UI-created programs {program_ids}: {exc}")
