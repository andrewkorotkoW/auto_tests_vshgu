"""Фильтр «Курсы с чатом ИИ» в списке активити — реальное имя параметра уточнено
в разведке: filters[is_llm_chat_enabled]=1, а не filters[llm_chat]=1
(docs/ai_chat_recon.md, раздел 1.7; docs/plans/2026-10-07_ai_chat_pmi_mission.md, Часть 2, п.4).
"""
from urllib.parse import urlencode

import allure
import pytest

from api.helpers.expectations import expect_status
from tests.api.ai_chat._helpers import unique_context_file


@allure.feature("Чат с ИИ в курсах")
@allure.story("Фильтр «Курсы с чатом ИИ»")
@pytest.mark.api
@pytest.mark.ai_chat
class TestLlmChatFilter:

    @allure.title("filters[is_llm_chat_enabled]=1 возвращает только активити с включённым чатом")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    def test_filter_returns_only_activities_with_ai_chat(
        self, api_client, created_tincan, llm_chat_endpoint, tmp_path
    ):
        with allure.step("Создать активити без чата с ИИ"):
            tincan_without_chat = created_tincan()

        with allure.step("Создать активити с настроенным и обработанным чатом с ИИ"):
            tincan_with_chat = created_tincan()
            content_id = tincan_with_chat["id"]
            context_file = unique_context_file(tmp_path)
            uploaded = llm_chat_endpoint.upload_files([context_file])
            storage_uuid = uploaded[0]["uuid"]
            llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
            llm_chat_endpoint.wait_processed(content_id)

        with allure.step("GET /activities?filters[is_llm_chat_enabled]=1 — только активити с чатом"):
            query = urlencode({"per-page": 100, "page": 1, "filters[is_llm_chat_enabled]": 1})
            resp = api_client.get(f"/activities?{query}")
            expect_status(resp, 200)
            ids_with_chat_enabled = {item["id"] for item in resp.json()["data"]}

            assert tincan_with_chat["id"] in ids_with_chat_enabled, (
                f"Активити {tincan_with_chat['id']} с включённым чатом не попала в фильтр "
                f"is_llm_chat_enabled=1"
            )
            assert tincan_without_chat["id"] not in ids_with_chat_enabled, (
                f"Активити {tincan_without_chat['id']} без чата с ИИ попала в фильтр "
                f"is_llm_chat_enabled=1"
            )
