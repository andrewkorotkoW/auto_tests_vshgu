"""ПМИ, шаг 10: загрузка TXT/PDF/MD (помимо DOCX, см. test_upload_docx_history.py) —
каждый формат обрабатывается до knowledge.status == completed (docs/ai_chat_recon.md, 1.2).
"""
import allure
import pytest

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("Загрузка файлов через UI")
class TestAiChatUploadFormats:

    @allure.title("Автотест_Загрузка файла формата {file_format} → обработка завершается успешно")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    @pytest.mark.parametrize(
        "file_format, source_path",
        [
            ("txt", "test_data/llm/soups.txt"),
            ("pdf", "test_data/llm/soups.pdf"),
            ("md", "test_data/llm/pea_soup.md"),
        ],
    )
    def test_upload_format(
        self, admin_page, env, created_tincan, llm_chat_endpoint, unique_llm_file, file_format, source_path
    ):
        allure.dynamic.parameter("file_format", file_format)

        with allure.step("1. Создать курс Tincan и открыть карточку на вкладке «Чат с ИИ»"):
            course = created_tincan()
            content_id = course["id"]
            ai_chat_page = AdminActivityAiChatPage(admin_page)
            ai_chat_page.open_card(env.ui_base_url, content_id)

        with allure.step("2. Включить переключатель"):
            ai_chat_page.toggle_switch()

        with allure.step(f"3. Загрузить файл формата {file_format} через зону загрузки"):
            local_path = unique_llm_file(source_path)
            ai_chat_page.upload_file(local_path)

        with allure.step("4. Дождаться обработки контекста (API, до 180 с) — статус completed"):
            knowledge = llm_chat_endpoint.wait_processed(content_id)
            assert knowledge["knowledge"]["status"] == "completed"

        with allure.step("5. Файл отображается в списке"):
            ai_chat_page.open_card(env.ui_base_url, content_id)
            assert ai_chat_page.file_rows.count() >= 1
