"""Админка (global) → «База знаний → Достижения»: создание достижения с условием
«Количество материалов» и иконкой — по одному сценарию на каждый тип материала.

Перенос test_01..06_admin_create_achievement_material_count*.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: Page Object вместо локаторов в тесте,
teardown через API (KnowledgeBaseEndpoint.delete_achievement) — у коллеги сценарий был
без teardown.
"""
from pathlib import Path

import allure
import pytest

from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"

# material_type (ключ API) -> русская подпись условия в достижении, для allure.title
MATERIAL_TYPE_TITLES = {
    "article": "статья",
    "video": "видео",
    "audio": "аудио",
    "book": "книга",
    "file": "файл",
    "course": "курс",
}


@allure.feature("База знаний UI")
@allure.story("Админка: создание достижения")
class TestCreateAchievement:

    @allure.title("UI: Администратор создаёт достижение «Количество материалов = 1 статья» с иконкой")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_achievement(self, admin_page, api_client, env):
        kb_page = AdminKnowledgeBasePage(admin_page)
        icon_path = TEST_DATA_DIR / "achievement_icon.png"
        achievement_id = None

        with allure.step("1. Проверить, что файл иконки подготовлен"):
            assert icon_path.exists(), f"Файл иконки не найден: {icon_path}"
            assert icon_path.stat().st_size <= 200 * 1024, (
                f"Иконка больше 200 КБ: {icon_path.stat().st_size} байт"
            )

        try:
            with allure.step("2. Открыть форму создания достижения"):
                kb_page.open_achievements_create_form(env.ui_base_url)

            with allure.step("3. Заполнить название, описание, загрузить иконку"):
                achievement_name = f"Автотест достижение {unique_suffix()}"
                achievement_description = "Автотестовое достижение: изучить 1 материал"
                kb_page.fill_achievement_name(achievement_name)
                kb_page.fill_achievement_description(achievement_description)
                kb_page.upload_achievement_icon(icon_path)

            with allure.step("4. Добавить условие «Количество материалов»: тип «Статья», количество 1"):
                kb_page.add_material_count_condition(material_type="Статья", count="1")

            with allure.step("5. Сохранить достижение"):
                achievement_id = kb_page.save_achievement_and_get_id()

            with allure.step("6. Проверить, что достижение появилось в списке созданных"):
                kb_page.expect_achievement_created(achievement_name)
                logger.info(f"Достижение создано в UI: ID={achievement_id}, name={achievement_name}")
        finally:
            with allure.step("7. Удалить достижение через API"):
                if achievement_id is not None:
                    KnowledgeBaseEndpoint(api_client).delete_achievement(achievement_id)
                    logger.info(f"Достижение удалено: ID={achievement_id}")
                else:
                    logger.warning("achievement_id не получен — удалять через API нечего")

    @pytest.mark.parametrize("material_type", ["video", "audio", "book", "file", "course"])
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_achievement_material_count_for_type(self, admin_page, api_client, env, material_type):
        allure.dynamic.title(
            f"UI: Администратор создаёт достижение «Количество материалов = 1 "
            f"{MATERIAL_TYPE_TITLES[material_type]}» с иконкой"
        )
        kb_page = AdminKnowledgeBasePage(admin_page)
        icon_path = TEST_DATA_DIR / "achievement_icon.png"
        achievement_id = None

        assert icon_path.exists(), f"Файл иконки не найден: {icon_path}"

        try:
            achievement_name = f"Автотест достижение {material_type} {unique_suffix()}"
            achievement_description = (
                f"Автотестовое достижение: изучить 1 материал типа «{MATERIAL_TYPE_TITLES[material_type]}»"
            )
            with allure.step(
                f"1-6. Создать достижение с условием «Количество материалов»: "
                f"тип «{MATERIAL_TYPE_TITLES[material_type]}», количество 1"
            ):
                achievement_id = kb_page.create_achievement_with_material_count_icon_for_type(
                    ui_base_url=env.ui_base_url,
                    name=achievement_name,
                    description=achievement_description,
                    icon_path=icon_path,
                    material_type=material_type,
                    count="1",
                )
                logger.info(f"Достижение создано в UI: ID={achievement_id}, name={achievement_name}")
        finally:
            with allure.step("7. Удалить достижение через API"):
                if achievement_id is not None:
                    KnowledgeBaseEndpoint(api_client).delete_achievement(achievement_id)
                    logger.info(f"Достижение удалено: ID={achievement_id}")
                else:
                    logger.warning("achievement_id не получен — удалять через API нечего")
