"""Управление настроенным чатом с ИИ: удаление файла, выключение переключателя,
выгрузка истории (docs/ai_chat_recon.md, разделы 1.4-1.6;
docs/plans/2026-10-07_ai_chat_pmi_mission.md, Часть 2, п.4).

Контекст для этих тестов — не канонические файлы test_data/llm (они заняты тестами
test_llm_chat_setup.py/test_llm_chat_formats.py), а уникальный текст на каждый вызов
(tests/api/ai_chat/_helpers.py) — чтобы не грузить повторно один и тот же по хэшу
файл несколько раз за прогон, см. docs/ai_chat_recon.md, раздел 4, п.1.
"""
import allure
import pytest

from api.helpers.expectations import expect_status
from tests.api.ai_chat._helpers import unique_context_file


def _setup_completed_chat(created_tincan, llm_chat_endpoint, tmp_path):
    tincan = created_tincan()
    content_id = tincan["id"]
    context_file = unique_context_file(tmp_path)
    uploaded = llm_chat_endpoint.upload_files([context_file])
    storage_uuid = uploaded[0]["uuid"]
    chat = llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
    llm_chat_endpoint.wait_processed(content_id)
    return tincan, storage_uuid, chat


@allure.feature("Чат с ИИ в курсах")
@allure.story("Управление настроенным чатом")
@pytest.mark.api
@pytest.mark.ai_chat
class TestLlmChatManagement:

    @allure.title("Удаление файла (remove_file) убирает его из знания")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    def test_remove_file(self, created_tincan, llm_chat_endpoint, tmp_path):
        with allure.step("Настроить чат и дождаться completed"):
            tincan, storage_uuid, chat = _setup_completed_chat(created_tincan, llm_chat_endpoint, tmp_path)
            content_id = tincan["id"]

        with allure.step("Удалить файл через remove_file"):
            llm_chat_endpoint.remove_file(chat["llm_knowledge_uuid"], storage_uuid)

        with allure.step("Файла больше нет в knowledge.files/meta.files"):
            data = llm_chat_endpoint.get(content_id)
            knowledge = data["knowledge"]
            assert storage_uuid not in (knowledge.get("files") or {}), "storage_uuid всё ещё в knowledge.files"
            assert not (knowledge.get("meta") or {}).get("files"), "meta.files не опустел после удаления файла"

    @allure.title("Выключение чата (disable/PATCH) переводит is_llm_chat_enabled в false")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive")
    def test_disable_chat(self, api_client, created_tincan, llm_chat_endpoint, tmp_path):
        with allure.step("Настроить чат и дождаться терминального статуса"):
            tincan, _storage_uuid, _chat = _setup_completed_chat(created_tincan, llm_chat_endpoint, tmp_path)
            content_id = tincan["id"]

        with allure.step("PATCH /content/{id}/llm-chat — выключить переключатель"):
            result = llm_chat_endpoint.disable(content_id)
            assert result["status"] == "success"

        with allure.step("is_enabled == false в GET /content/{id}/llm-chat"):
            data = llm_chat_endpoint.get(content_id)
            assert data["is_enabled"] is False

        with allure.step("is_llm_chat_enabled == false в GET /content/{id}"):
            resp = api_client.get(f"/content/{content_id}")
            expect_status(resp, 200)
            assert resp.json()["data"]["is_llm_chat_enabled"] is False

    @allure.title("Выгрузка истории (export) -> 200, status: success")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("api", "positive")
    def test_export_history(self, created_tincan, llm_chat_endpoint, tmp_path):
        with allure.step("Настроить чат и дождаться терминального статуса"):
            tincan, _storage_uuid, _chat = _setup_completed_chat(created_tincan, llm_chat_endpoint, tmp_path)
            content_id = tincan["id"]

        with allure.step("GET /content/{id}/llm-chat/export -> 200 {status: success}"):
            result = llm_chat_endpoint.export(content_id)
            assert result["status"] == "success", f"Неожиданный ответ экспорта: {result}"
