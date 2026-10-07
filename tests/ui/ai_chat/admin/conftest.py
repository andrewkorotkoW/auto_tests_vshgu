"""Локальные фикстуры для tests/ui/ai_chat/admin.

Чат с ИИ общий для всех типов активити (значок/фильтр привязаны к is_llm_chat_enabled,
не к content_type — docs/ai_chat_recon.md, 1.8), поэтому тестам значка/фильтра нужна
активити любого типа (tincan|scorm), а не только Tincan из общей фикстуры created_tincan.
"""
import pytest

from api.helpers.data_generator import generate_scorm_payload, generate_tincan_payload


@pytest.fixture
def course_factory(tincan_endpoint):
    """Создаёт активити типа tincan или scorm через API, удаляет после теста (даже при
    падении) — используется там, где фича общая для типов активити, а не специфична
    для плеера Tincan."""
    content_ids = []

    def _create(content_type: str = "tincan"):
        cover_uuid = tincan_endpoint.upload_cover()
        if content_type == "scorm":
            archive_uuid = tincan_endpoint.upload_archive("test_data/test_lms_scorm_2004.zip")
            payload = generate_scorm_payload(archive_uuid=archive_uuid, cover_uuid=cover_uuid)
        elif content_type == "tincan":
            archive_uuid = tincan_endpoint.upload_archive()
            payload = generate_tincan_payload(archive_uuid=archive_uuid, cover_uuid=cover_uuid)
        else:
            raise ValueError(f"Неизвестный content_type: {content_type}")
        data = tincan_endpoint.create(payload)
        content_ids.append(data["id"])
        return {"id": data["id"], "name": data["attributes"]["name"], "attributes": data["attributes"]}

    yield _create

    if content_ids:
        tincan_endpoint.mass_delete(content_ids)
