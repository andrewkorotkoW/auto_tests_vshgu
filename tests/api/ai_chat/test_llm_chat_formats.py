"""Форматы контекста чата с ИИ: поддерживаемые (txt/pdf/md -> completed), скан без
текста (-> empty_context, knowledge.status failed) и короткий документ (-> short_context)
(docs/ai_chat_recon.md, раздел 1.2; docs/plans/2026-10-07_ai_chat_pmi_mission.md, Часть 2, п.4).
"""
import allure
import pytest

SOUPS_TXT = "test_data/llm/soups.txt"
SOUPS_PDF = "test_data/llm/soups.pdf"
PEA_SOUP_MD = "test_data/llm/pea_soup.md"
SCAN_IMAGES_ONLY_PDF = "test_data/llm/scan_images_only.pdf"
SHORT_DOCX = "test_data/practical_task_main_document.docx"


@allure.feature("Чат с ИИ в курсах")
@allure.story("Форматы контекста")
@pytest.mark.api
@pytest.mark.ai_chat
class TestLlmChatFormats:

    @allure.title("Поддерживаемый формат контекста доходит до completed")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "positive")
    @pytest.mark.parametrize(
        "file_path",
        [
            pytest.param(SOUPS_TXT, id="txt"),
            pytest.param(SOUPS_PDF, id="pdf"),
            pytest.param(PEA_SOUP_MD, id="md"),
        ],
    )
    def test_format_reaches_completed(self, created_tincan, llm_chat_endpoint, file_path):
        with allure.step(f"Создать активити и загрузить {file_path}"):
            tincan = created_tincan()
            content_id = tincan["id"]
            uploaded = llm_chat_endpoint.upload_files([file_path])
            storage_uuid = uploaded[0]["uuid"]
            llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)

        with allure.step("Дождаться completed"):
            data = llm_chat_endpoint.wait_processed(content_id)
            knowledge = data["knowledge"]
            statuses = {file_info["status"] for file_info in knowledge["meta"]["files"].values()}
            assert statuses == {"completed"}, f"{file_path}: статусы файлов {statuses}"
            assert knowledge["status"] == "completed", f"{file_path}: knowledge.status {knowledge['status']}"

    @allure.title("Скан без текста (scan_images_only.pdf) -> empty_context, knowledge.status failed")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    def test_scan_without_text_reaches_empty_context(self, created_tincan, llm_chat_endpoint):
        with allure.step(f"Создать активити и загрузить {SCAN_IMAGES_ONLY_PDF}"):
            tincan = created_tincan()
            content_id = tincan["id"]
            uploaded = llm_chat_endpoint.upload_files([SCAN_IMAGES_ONLY_PDF])
            storage_uuid = uploaded[0]["uuid"]
            llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)

        with allure.step("Дождаться терминального статуса — empty_context, knowledge.status failed"):
            data = llm_chat_endpoint.wait_processed(content_id)
            knowledge = data["knowledge"]
            statuses = {file_info["status"] for file_info in knowledge["meta"]["files"].values()}
            assert statuses == {"empty_context"}, f"Статусы файлов: {statuses}"
            assert knowledge["status"] == "failed", f"knowledge.status: {knowledge['status']}"

    @allure.title("Короткий документ (practical_task_main_document.docx) -> short_context")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("api", "negative")
    def test_short_document_reaches_short_context(self, created_tincan, llm_chat_endpoint):
        with allure.step(f"Создать активити и загрузить {SHORT_DOCX}"):
            tincan = created_tincan()
            content_id = tincan["id"]
            uploaded = llm_chat_endpoint.upload_files([SHORT_DOCX])
            storage_uuid = uploaded[0]["uuid"]
            llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)

        with allure.step("Дождаться терминального статуса — short_context"):
            data = llm_chat_endpoint.wait_processed(content_id)
            knowledge = data["knowledge"]
            statuses = {file_info["status"] for file_info in knowledge["meta"]["files"].values()}
            assert statuses == {"short_context"}, f"Статусы файлов: {statuses}"
