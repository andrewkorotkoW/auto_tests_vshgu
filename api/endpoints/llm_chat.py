import mimetypes
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

# docs/ai_chat_recon.md, 1.2/1.4: статусы файла знания и knowledge.status, после которых
# дальнейший опрос GET /content/{id}/llm-chat не меняет результат.
TERMINAL_FILE_STATUSES = {"completed", "short_context", "empty_context"}
TERMINAL_KNOWLEDGE_STATUSES = {"completed", "failed"}


class LlmChatEndpoint:
    """Методы для работы с чатом с ИИ в курсах (/content/{id}/llm-chat, /llm-knowledge/{uuid}/files,
    /upload/llm_knowledge_files) — см. docs/ai_chat_recon.md."""

    def __init__(self, client: ApiClient):
        self.client = client

    def get(self, content_id: int) -> Optional[Dict]:
        """GET /content/{id}/llm-chat — None, пока чат не настроен (ответ {"data": null})."""
        resp = self.client.get(f"/content/{content_id}/llm-chat")
        expect_status(resp, 200)
        return resp.json().get("data")

    def upload_files(self, file_paths: List[Union[str, Path]]) -> List[Dict]:
        """POST /upload/llm_knowledge_files — multipart, поле файла **files[]** (не files
        и не file — без этого backend отвечает 422, см. docs/ai_chat_recon.md, 1.2).
        Возвращает список элементов data (uuid + attributes) в порядке file_paths."""
        opened = []
        try:
            files_payload = []
            for raw_path in file_paths:
                file_path = Path(raw_path)
                guessed_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                fh = file_path.open("rb")
                opened.append(fh)
                files_payload.append(("files[]", (file_path.name, fh, guessed_type)))
            resp = self.client.upload("/upload/llm_knowledge_files", files=files_payload)
        finally:
            for fh in opened:
                fh.close()
        expect_status(resp, (200, 201))
        data = resp.json().get("data")
        if not isinstance(data, list) or not data:
            raise AssertionError(f"Ответ загрузки файлов чата с ИИ без data: {resp.text[:500]}")
        return data

    def setup(self, content_id: int, file_uuids: List[str], is_enabled: int = 1) -> Dict:
        """POST /content/{id}/llm-chat {"files": [...], "is_enabled": 1} → 201 — включает
        переключатель и создаёт/дополняет знание первой привязкой файлов."""
        resp = self.client.post(
            f"/content/{content_id}/llm-chat",
            json={"files": file_uuids, "is_enabled": is_enabled},
        )
        expect_status(resp, 201)
        data = resp.json()["data"]
        logger.info(f"LLM chat настроен для активити {content_id}: id={data.get('id')}")
        return data

    def disable(self, content_id: int) -> Dict:
        """PATCH /content/{id}/llm-chat с пустым телом — выключает переключатель
        (is_llm_chat_enabled → false), см. docs/ai_chat_recon.md, 1.5."""
        resp = self.client.patch(f"/content/{content_id}/llm-chat", json={})
        expect_status(resp, 200)
        return resp.json()["data"]

    def add_file(self, llm_knowledge_uuid: str, storage_uuid: str) -> Dict:
        """PATCH /llm-knowledge/{uuid}/files {"operation": "add"} — добавление файла
        к уже настроенному знанию, см. docs/ai_chat_recon.md, 1.3."""
        resp = self.client.patch(
            f"/llm-knowledge/{llm_knowledge_uuid}/files",
            json={"files": [storage_uuid], "operation": "add"},
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def remove_file(self, llm_knowledge_uuid: str, storage_uuid: str) -> Dict:
        """PATCH /llm-knowledge/{uuid}/files {"operation": "remove"} — тело использует
        llm_storage_uuid (ключ knowledge.files), не file_uuid (ключ knowledge.meta.files)
        и не numeric id, см. docs/ai_chat_recon.md, 1.4."""
        resp = self.client.patch(
            f"/llm-knowledge/{llm_knowledge_uuid}/files",
            json={"files": [storage_uuid], "operation": "remove"},
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def export(self, content_id: int) -> Dict:
        """GET /content/{id}/llm-chat/export → 200 {"status": "success"} — файл истории
        формируется асинхронно, содержимое автотестом не проверяется."""
        resp = self.client.get(f"/content/{content_id}/llm-chat/export")
        expect_status(resp, 200)
        return resp.json()["data"]

    def wait_processed(self, content_id: int, timeout: int = 180, poll_interval: float = 5.0) -> Dict:
        """Опрос GET /content/{id}/llm-chat до терминального статуса каждого файла знания
        (completed/short_context/empty_context) и knowledge.status (completed/failed) —
        цикл с дедлайном, без sleep с магическим числом (см. docs/ai_chat_recon.md, 1.2)."""
        deadline = time.monotonic() + timeout
        last_data = None
        while True:
            last_data = self.get(content_id)
            if last_data:
                knowledge = last_data.get("knowledge") or {}
                files_meta = (knowledge.get("meta") or {}).get("files") or {}
                statuses = [file_info.get("status") for file_info in files_meta.values()]
                files_terminal = bool(statuses) and all(status in TERMINAL_FILE_STATUSES for status in statuses)
                knowledge_terminal = knowledge.get("status") in TERMINAL_KNOWLEDGE_STATUSES
                if files_terminal and knowledge_terminal:
                    return last_data
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Контекст чата с ИИ активити {content_id} не обработан за {timeout} с: {last_data}"
                )
            time.sleep(poll_interval)
