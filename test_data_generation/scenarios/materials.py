"""Сценарий materials: N материалов базы знаний каждого «самостоятельного» типа —
статья (текст прямо в payload), книга и файл (PDF test_data/certificat.pdf), аудио
(test_data/audio.mp3), видео (test_data/video.mp4) — через те же методы
KnowledgeBaseEndpoint.create_article_material/create_file_material, что и фикстуры
tests/ui/knowledge_base/user_achievements/conftest.py. Материал типа «курс» — в сценарии
courses (ему нужна активность Tincan). Все материалы создаются видимыми.
"""
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from utils.logger import logger

DESCRIPTION = "N материалов БЗ каждого типа: статья / книга / файл / аудио / видео"
COUNT_HELP = "материалов каждого из пяти типов"

# material_type -> (файл в test_data/, content_type, duration) — как FILE_BACKED_MATERIALS
# в tests/ui/knowledge_base/user_achievements/conftest.py.
FILE_BACKED = {
    "book": ("test_data/certificat.pdf", "application/pdf", 0),
    "file": ("test_data/certificat.pdf", "application/pdf", 0),
    "audio": ("test_data/audio.mp3", "audio/mpeg", 60),
    "video": ("test_data/video.mp4", "video/mp4", 60),
}


def run(ctx) -> None:
    kb_ep = KnowledgeBaseEndpoint(ctx.api_client)

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""

        logger.info(f"Статья {i + 1}/{ctx.count}...")
        article = kb_ep.create_article_material(
            name=ctx.name(f"Article{suffix}"),
            article_text=f"<p>Текст статьи {ctx.name(f'Article{suffix}')} (сгенерировано test_data_generation)</p>",
        )
        ctx.manifest.record("knowledge_base_material", article["id"], "knowledge_base.delete_materials([id])")

        for material_type, (file_path, content_type, duration) in FILE_BACKED.items():
            logger.info(f"Материал «{material_type}» {i + 1}/{ctx.count} ({file_path})...")
            material = kb_ep.create_file_material(
                name=ctx.name(f"{material_type.capitalize()}{suffix}"),
                material_type=material_type,
                file_path=file_path,
                content_type=content_type,
                duration=duration,
            )
            ctx.manifest.record("knowledge_base_material", material["id"], "knowledge_base.delete_materials([id])")

    logger.info("Готово.")
