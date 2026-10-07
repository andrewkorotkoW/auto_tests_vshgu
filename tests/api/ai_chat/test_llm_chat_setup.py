"""Контракт настройки чата с ИИ (docs/ai_chat_recon.md, разделы 1.1-1.2;
docs/plans/2026-10-07_ai_chat_pmi_mission.md, Часть 2, п.4).
"""
from urllib.parse import urlencode

import allure
import pytest

from api.helpers.expectations import expect_status


@allure.feature("Чат с ИИ в курсах")
@allure.story("Настройка чата")
@pytest.mark.api
@pytest.mark.ai_chat
class TestLlmChatSetup:

    @allure.title("У новой активити без настроенного чата GET /content/{id}/llm-chat -> data: null")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    def test_empty_chat_for_new_activity(self, created_tincan, llm_chat_endpoint):
        with allure.step("Создать активити Tincan без настройки чата с ИИ"):
            tincan = created_tincan()
            content_id = tincan["id"]

        with allure.step("GET /content/{id}/llm-chat -> data: null"):
            data = llm_chat_endpoint.get(content_id)
            assert data is None, f"Ожидали data: null у новой активити, получили: {data}"

    @allure.title("Настройка чата с soups.docx доходит до completed, is_llm_chat_enabled включается")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("api", "positive", "smoke")
    @pytest.mark.smoke
    def test_setup_with_docx_reaches_completed(self, api_client, tincan_with_ai_chat):
        activity = tincan_with_ai_chat
        content_id = activity["id"]
        setup_response = activity["knowledge"]

        with allure.step("Статус файла и статус знания — completed, переключатель включён"):
            knowledge = setup_response["knowledge"]
            files_meta = knowledge["meta"]["files"]
            assert files_meta, "Нет файлов в knowledge.meta.files"
            statuses = {file_info["status"] for file_info in files_meta.values()}
            assert statuses == {"completed"}, f"Ожидали completed у всех файлов, получили: {statuses}"
            assert knowledge["status"] == "completed", f"knowledge.status: {knowledge['status']}"
            assert setup_response["is_enabled"] is True

        with allure.step("is_llm_chat_enabled == true в GET /content/{id}"):
            resp = api_client.get(f"/content/{content_id}")
            expect_status(resp, 200)
            assert resp.json()["data"]["is_llm_chat_enabled"] is True

        with allure.step("is_llm_chat_enabled == true в строке GET /activities"):
            query = urlencode({"per-page": 25, "page": 1, "filters[name]": activity["name"]})
            resp = api_client.get(f"/activities?{query}")
            expect_status(resp, 200)
            rows = [item for item in resp.json()["data"] if item["id"] == content_id]
            assert rows, f"Активити {content_id} не найдена в GET /activities по имени {activity['name']!r}"
            assert rows[0]["is_llm_chat_enabled"] is True
