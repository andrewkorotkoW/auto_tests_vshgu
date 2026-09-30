"""Фикстуры для API-тестов взаимопроверки ПЗ (p2p) — каркас до разработки
(докs/missions/2026-09-30_tz2026_p2p.md, docs/test_cases/p2p/). Все тесты этого пакета
пропускаются автоматически, пока функциональность не подтверждена на ветке — см.
skip_if_p2p_not_ready и config/environments.py::is_feature_ready("P2P_READY").
"""
import pytest

from api.endpoints.p2p import P2PEndpoint
from config.environments import is_feature_ready


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
