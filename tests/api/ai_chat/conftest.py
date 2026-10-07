"""Фикстуры для API-тестов «Чат с ИИ в курсах» (docs/plans/2026-10-07_ai_chat_pmi_mission.md,
docs/ai_chat_recon.md) — по образцу tests/api/cas.

api_client/created_tincan/tincan_endpoint/llm_chat_endpoint — общие фикстуры из корневого
conftest.py, здесь не переопределяются.
"""
import pytest

SOUPS_DOCX = "test_data/llm/soups.docx"


@pytest.fixture
def tincan_with_ai_chat(created_tincan, llm_chat_endpoint):
    """Готовый Tincan с настроенным и обработанным чатом с ИИ: загружен test_data/llm/soups.docx,
    переключатель включён, знание дождалось knowledge.status == completed (docs/ai_chat_recon.md,
    1.2). Активити удаляет teardown created_tincan — отрабатывает даже при падении теста."""
    tincan = created_tincan()
    content_id = tincan["id"]

    uploaded = llm_chat_endpoint.upload_files([SOUPS_DOCX])
    storage_uuid = uploaded[0]["uuid"]
    llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
    knowledge = llm_chat_endpoint.wait_processed(content_id)

    return {
        "id": content_id,
        "name": tincan["name"],
        "attributes": tincan["attributes"],
        "storage_uuid": storage_uuid,
        "knowledge": knowledge,
    }
