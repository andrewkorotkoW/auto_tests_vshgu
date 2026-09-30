"""Фикстуры для UI-тестов взаимопроверки ПЗ (p2p) — каркас до разработки
(docs/missions/2026-09-30_tz2026_p2p.md, docs/test_cases/p2p/). Все тесты этого пакета
пропускаются автоматически, пока функциональность не подтверждена на ветке — см.
skip_if_p2p_not_ready и config/environments.py::is_feature_ready("P2P_READY").

browser/admin_page/user_page/env — общие фикстуры из корневого conftest.py, здесь не
переопределяются.
"""
import pytest

from api.endpoints.p2p import P2PEndpoint
from config.environments import is_feature_ready
from utils.logger import logger


@pytest.fixture(autouse=True)
def skip_if_p2p_not_ready():
    """Пропускает все тесты пакета, если флаг P2P_READY не выставлен в .env (см.
    .env.example) — до появления ветки с реализацией взаимопроверки ПЗ селекторы
    ui/pages/external_review_page.py и расширений practical_task_page.py/reviewer_page.py
    не подтверждены и реальный прогон бессмысленен."""
    if not is_feature_ready("P2P_READY"):
        pytest.skip("P2P_READY не выставлен — взаимопроверка ПЗ ещё не реализована на этом стенде")


@pytest.fixture
def p2p_endpoint(api_client):
    return P2PEndpoint(api_client)


@pytest.fixture
def p2p_practical_task(created_stream, created_module, created_homework, assignments_endpoint,
                        homework_endpoint, p2p_endpoint):
    """Создаёт поток → модуль → ПЗ, добавляет ПЗ в модуль и включает взаимопроверку —
    общая подготовка для UI-тестов слушателя-проверяющего/внешнего проверяющего
    (по аналогии с tests/ui/practical_tasks/groups/conftest.py::group_practical_task).
    Удаляет ПЗ после теста (поток/программу удаляет created_stream)."""
    homework_ids = []

    def _create(*, cover_uuid, archive_uuid, **kwargs):
        stream_kwargs = {k: kwargs.pop(k) for k in ("name",) if k in kwargs}
        stream = created_stream(**stream_kwargs)
        module = created_module(program_id=stream["program_id"], stream_id=stream["id"])
        homework = created_homework(cover_uuid=cover_uuid, archive_uuid=archive_uuid, **kwargs)
        homework_ids.append(homework["id"])

        p2p_endpoint.enable_peer_review(homework["id"])

        assigned_ok = assignments_endpoint.assign_content_to_module(
            stream["program_id"], stream["id"], module["id"], [homework["id"]]
        )
        assert assigned_ok, "Не удалось добавить P2P-ПЗ в модуль"

        return stream, module, homework

    yield _create

    for homework_id in homework_ids:
        try:
            homework_endpoint.mass_delete([homework_id])
        except Exception as e:
            logger.warning(f"Failed to delete p2p homework {homework_id}: {e}")
