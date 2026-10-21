"""Сценарий achievements: N достижений с условием «изучено N материалов типа статья»
(KnowledgeBaseEndpoint.create_achievement, тот же путь, что у фикстуры created_achievement
в conftest.py) — активные, со стандартной иконкой из GET /admin/achievements/
achievement-default-icons. Отдельно от activities: достижение не привязано к программе,
а пересчёт выдачи идёт по материалам БЗ (см. память vshgu_achievements_contract).
"""
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from utils.logger import logger

DESCRIPTION = "N достижений с условием «изучено N материалов-статей», активные"
COUNT_HELP = "достижений"


def run(ctx) -> None:
    kb_ep = KnowledgeBaseEndpoint(ctx.api_client)

    # В dry-run DryRunClient отдаёт data-словарь, а не список иконок — uuid подставляется фейковый.
    icon_uuid = ctx.dry_or(
        "GET /admin/achievements/achievement-default-icons (uuid стандартной иконки)",
        "00000000-0000-0000-0000-00000000icon",
        kb_ep.get_default_achievement_icon_uuid,
    )

    for i in range(ctx.count):
        suffix = f"_{i + 1}" if ctx.count > 1 else ""
        logger.info(f"Достижение {i + 1}/{ctx.count} (условие: {i + 1} материал(ов) типа статья)...")
        achievement = kb_ep.create_achievement({
            "name": ctx.name(f"Achievement{suffix}"),
            "description": "Автотестовое достижение (сгенерировано test_data_generation)",
            "is_active": True,
            "icon_uuid": icon_uuid,
            "conditions": [{"type": "material_count", "count": i + 1, "material_type": "article"}],
        })
        ctx.manifest.record("achievement", achievement["id"], "knowledge_base.delete_achievement(id)")

    logger.info("Готово.")
