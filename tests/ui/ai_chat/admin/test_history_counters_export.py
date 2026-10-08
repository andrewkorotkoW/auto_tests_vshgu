"""ПМИ, шаги 20-21: блок «История ИИ-чата» — счётчики «Задано вопросов»/«Получено
ответов» (изначально 0 — слушатель ещё не задавал вопросов) и кнопка «Скачать историю»
(GET /content/{id}/llm-chat/export → 200 {status: success}, файл асинхронный, его
содержимое — ручной кейс, docs/ai_chat_recon.md, 1.6).
"""
import allure
import pytest

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("История чата: счётчики и экспорт")
class TestAiChatHistoryCountersExport:

    @allure.title("Автотест_Счётчики вопросов/ответов и кнопка «Скачать историю» (export → 200 success)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_counters_and_download_history(self, admin_page, env, tincan_with_ai_chat):
        content_id = tincan_with_ai_chat["id"]
        ai_chat_page = AdminActivityAiChatPage(admin_page)

        with allure.step("1. Открыть карточку — счётчики нулевые (вопросов ещё не было)"):
            ai_chat_page.open_card(env.ui_base_url, content_id)
            assert ai_chat_page.questions_count() == "0"
            assert ai_chat_page.answers_count() == "0"

        with allure.step("2. «Скачать историю» → GET /content/{id}/llm-chat/export отвечает 200 status: success"):
            with admin_page.expect_response(
                lambda r: f"/content/{content_id}/llm-chat/export" in r.url
            ) as response_info:
                ai_chat_page.click_download_history()
            response = response_info.value
            assert response.status == 200
            assert response.json()["data"]["status"] == "success"
