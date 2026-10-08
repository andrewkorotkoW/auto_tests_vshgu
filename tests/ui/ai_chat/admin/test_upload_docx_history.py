"""ПМИ, шаг 9: загрузка DOCX через зону загрузки (UI) — файл появляется в списке,
появляется блок «История ИИ-чата» (docs/ai_chat_recon.md, 1.2, 3.1).
"""
import allure
import pytest

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage

SOUPS_DOCX = "test_data/llm/soups.docx"


@allure.feature("Чат с ИИ в курсах")
@allure.story("Загрузка файлов через UI")
class TestAiChatUploadDocxHistory:

    @allure.title("Автотест_Загрузка DOCX через зону загрузки → файл в списке, появляется «История ИИ-чата»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_upload_docx_shows_file_and_history(
        self, admin_page, env, created_tincan, llm_chat_endpoint, unique_llm_file
    ):
        with allure.step("1. Создать курс Tincan и открыть карточку на вкладке «Чат с ИИ»"):
            course = created_tincan()
            content_id = course["id"]
            ai_chat_page = AdminActivityAiChatPage(admin_page)
            ai_chat_page.open_card(env.ui_base_url, content_id)

        with allure.step("2. Включить переключатель"):
            ai_chat_page.toggle_switch()
            assert ai_chat_page.context_block.is_visible(timeout=15000)

        with allure.step("3. Загрузить soups.docx через зону загрузки (expect_file_chooser)"):
            local_path = unique_llm_file(SOUPS_DOCX)
            ai_chat_page.upload_file(local_path)

        with allure.step("4. Дождаться обработки контекста (API, до 180 с)"):
            knowledge = llm_chat_endpoint.wait_processed(content_id)
            assert knowledge["knowledge"]["status"] == "completed"

        with allure.step("5. Обновить страницу и проверить файл в списке + блок «История ИИ-чата»"):
            ai_chat_page.open_card(env.ui_base_url, content_id)
            assert ai_chat_page.file_rows.count() >= 1
            assert ai_chat_page.history_block.is_visible(timeout=15000)
            assert ai_chat_page.history_title.is_visible(timeout=15000)
