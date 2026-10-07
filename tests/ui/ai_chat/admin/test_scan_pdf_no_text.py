"""ПМИ, шаг 11: PDF без текстового слоя (только изображения) → API: статус файла
empty_context, knowledge.status == failed; UI: подпись об ошибке. Известное расхождение
D2 — в UI не точный текст ПМИ «В документах не найден текст», а общая «Не удалось
обработать часть файлов.» — xfail(strict=False), см.
qa_analysis/cases/VSHGU2-2375_AI_chat_PMI_2026-09-29/report.md и docs/ai_chat_recon.md, п.4.3.
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage

SCAN_PDF = "test_data/llm/scan_images_only.pdf"


@allure.feature("Чат с ИИ в курсах")
@allure.story("Загрузка файлов через UI")
class TestAiChatScanPdfNoText:

    @allure.title("Автотест_Скан-PDF без текста → ошибка обработки (API: empty_context/failed)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_scan_pdf_fails_processing(self, admin_page, env, created_tincan, llm_chat_endpoint, unique_llm_file):
        with allure.step("1. Создать курс, открыть карточку, включить переключатель"):
            course = created_tincan()
            content_id = course["id"]
            ai_chat_page = AdminActivityAiChatPage(admin_page)
            ai_chat_page.open_card(env.ui_base_url, content_id)
            ai_chat_page.toggle_switch()

        with allure.step("2. Загрузить скан-PDF (только изображения, без текстового слоя)"):
            ai_chat_page.upload_file(unique_llm_file(SCAN_PDF))

        with allure.step("3. API: статус файла empty_context, knowledge.status == failed"):
            knowledge = llm_chat_endpoint.wait_processed(content_id)
            files_meta = knowledge["knowledge"]["meta"]["files"]
            statuses = [f["status"] for f in files_meta.values()]
            assert statuses == ["empty_context"], f"Неожиданный статус файла: {statuses}"
            assert knowledge["knowledge"]["status"] == "failed"

        with allure.step("4. UI: виден блок статуса ошибки"):
            ai_chat_page.open_card(env.ui_base_url, content_id)
            expect(ai_chat_page.status_block).to_be_visible(timeout=15000)
            assert ai_chat_page.is_error()

        with allure.step("5. (xfail D2) Подпись в точности «В документах не найден текст»"):
            status_text = ai_chat_page.status_block.text_content() or ""
            if "В документах не найден текст" not in status_text:
                pytest.xfail(
                    "Кандидат в дефект D2 (подтверждено разведкой 07.10.2026): "
                    f"вместо точной подписи ПМИ «В документах не найден текст» показана общая "
                    f"«{status_text.strip()}» — см. qa_analysis/cases/VSHGU2-2375_AI_chat_PMI_2026-09-29/report.md"
                )
