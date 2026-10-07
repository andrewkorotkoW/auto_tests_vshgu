import allure
import pytest

from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from utils.logger import logger


@pytest.fixture
def register_knowledge_base_material(api_client):
    """Регистрирует материалы, созданные через UI, для best-effort cleanup."""
    material_ids = []
    knowledge_base_endpoint = KnowledgeBaseEndpoint(api_client)

    def _register(material_id: int) -> None:
        material_ids.append(material_id)

    yield _register

    if material_ids:
        try:
            knowledge_base_endpoint.delete_materials(material_ids)
        except Exception as exc:  # noqa: BLE001 - cleanup не должен скрывать исходный фейл
            allure.attach(
                str(exc),
                name="knowledge_base_material_cleanup_error",
                attachment_type=allure.attachment_type.TEXT,
            )
            logger.warning(f"Failed to delete UI-created materials {material_ids}: {exc}")


@pytest.fixture
def register_knowledge_base_achievement(api_client):
    """Регистрирует достижения, созданные через UI, для best-effort cleanup."""
    achievement_ids = []
    knowledge_base_endpoint = KnowledgeBaseEndpoint(api_client)

    def _register(achievement_id: int) -> None:
        achievement_ids.append(achievement_id)

    yield _register

    for achievement_id in achievement_ids:
        try:
            knowledge_base_endpoint.delete_achievement(achievement_id)
        except Exception as exc:  # noqa: BLE001 - cleanup не должен скрывать исходный фейл
            allure.attach(
                str(exc),
                name="knowledge_base_achievement_cleanup_error",
                attachment_type=allure.attachment_type.TEXT,
            )
            logger.warning(f"Failed to delete UI-created achievement {achievement_id}: {exc}")
