"""Фикстуры для UI-тестов «Чат с ИИ в курсах» (docs/plans/2026-10-07_ai_chat_pmi_mission.md,
docs/ai_chat_recon.md) — по образцу tests/ui/cas. Общие для admin/ и user/.

api_client/created_tincan/tincan_endpoint/llm_chat_endpoint — общие фикстуры из корневого
conftest.py, здесь не переопределяются.
"""
import shutil
import time
import zipfile
from pathlib import Path

import pytest

SOUPS_DOCX = "test_data/llm/soups.docx"


def _unique_copy(source_path: str, dest_dir: Path) -> str:
    """Копия файла с уникальным (по хэшу) содержимым, но тем же текстом для ИИ.

    Обход подтверждённого живым прогоном дефекта стенда develop (docs/ai_chat_recon.md,
    раздел 4, п.1): backend дедуплицирует загруженные файлы по хэшу содержимого, и
    повторная загрузка файла, чей хэш уже был привязан к знанию, которое с тех пор
    удалено (а каждый тест удаляет свою активити в teardown — ровно это и происходит),
    навсегда зависает в статусе pending. Раз все тесты этой области грузят один и тот
    же test_data/llm/soups.docx и сами удаляют активити — без уникализации второй и
    все последующие тесты в прогоне гарантированно взяли бы 180-секундный таймаут.
    Для DOCX (это zip) добавляется отдельная, ничем не referenced запись в архив — не
    трогает document.xml, извлекаемый текст не меняется. Для остальных форматов в конец
    дописывается короткая метка — для PDF это байты после %%EOF (проверено живым
    прогоном: знание обрабатывается нормально, текст извлекается), для TXT/MD — лишняя
    строка в конце, не влияющая на вопросы по основному содержимому."""
    source = Path(source_path)
    nonce = f"{time.time_ns()}"
    dest = dest_dir / f"{source.stem}_{nonce}{source.suffix}"
    if source.suffix.lower() == ".docx":
        shutil.copyfile(source, dest)
        with zipfile.ZipFile(dest, "a") as zf:
            zf.writestr("autotest_nonce.txt", nonce)
    else:
        with open(dest, "wb") as f:
            f.write(source.read_bytes())
            f.write(f"\n% autotest-nonce {nonce}\n".encode("utf-8", errors="ignore"))
    return str(dest)


@pytest.fixture
def unique_llm_file(tmp_path):
    """Фабрика уникальных (по хэшу) копий тестовых файлов test_data/llm/* — см. _unique_copy.
    Используется везде, где тест сам загружает файл в чат с ИИ (а не только через
    tincan_with_ai_chat), иначе уже второй прогон с тем же файлом в сессии стенда
    (или просто второй тест в этом же прогоне) зависает в pending."""
    def _make(source_path: str) -> str:
        return _unique_copy(source_path, tmp_path)
    return _make


@pytest.fixture
def tincan_with_ai_chat(created_tincan, llm_chat_endpoint, unique_llm_file):
    """Готовый Tincan с настроенным и обработанным чатом с ИИ: загружен уникальный по
    хэшу вариант test_data/llm/soups.docx (см. unique_llm_file — обход дефекта
    дедупликации по хэшу), переключатель включён, знание дождалось
    knowledge.status == completed (docs/ai_chat_recon.md, 1.2). Активити удаляет
    teardown created_tincan — отрабатывает даже при падении теста."""
    tincan = created_tincan()
    content_id = tincan["id"]

    uploaded = llm_chat_endpoint.upload_files([unique_llm_file(SOUPS_DOCX)])
    storage_uuid = uploaded[0]["uuid"]
    llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
    knowledge = llm_chat_endpoint.wait_processed(content_id)

    return {
        "id": content_id,
        "name": tincan["name"],
        "attributes": tincan["attributes"],
        "storage_uuid": storage_uuid,
        "knowledge": knowledge,
    }
