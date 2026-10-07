"""Тестовый хелпер для tests/api/ai_chat — не трогает инфраструктуру
(api/endpoints/llm_chat.py, tests/api/ai_chat/conftest.py), только тестовый код,
по образцу tests/api/helpdesk/_known_defects.py.
"""
import uuid
from pathlib import Path

_PEA_SOUP_MD = Path("test_data/llm/pea_soup.md")


def unique_context_file(tmp_path: Path, suffix: str = ".txt") -> Path:
    """Копия текста test_data/llm/pea_soup.md с добавленной уникальной меткой — для
    тестов, которым не важен конкретный канонический файл test_data/llm, а нужен
    контекст, который гарантированно дойдёт до completed.

    docs/ai_chat_recon.md, раздел 4, п.1: повторная загрузка уже встречавшегося по
    хэшу содержимого иногда навсегда остаётся в pending у новой активити и блокирует
    удаление (423). Генерируя уникальный текст на каждый вызов, тест не зависит от
    того, сколько раз этот же сьют (или разведка) уже грузили тот же канонический файл.
    """
    marker = f"\n\nАвтотест, уникальная метка: {uuid.uuid4()}\n"
    text = _PEA_SOUP_MD.read_text(encoding="utf-8") + marker
    path = tmp_path / f"autotest_context_{uuid.uuid4().hex}{suffix}"
    path.write_text(text, encoding="utf-8")
    return path
