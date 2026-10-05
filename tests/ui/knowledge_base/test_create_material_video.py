"""Админка (global) → «База знаний → Материалы»: создание материала типа «Видео».

Перенос test_02_admin_create_video_material.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: Page Object вместо локаторов в тесте,
teardown через API вместо cleanup_manager.
"""
from pathlib import Path

import allure
import pytest

from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@allure.feature("База знаний UI")
@allure.story("Админка: создание материала «Видео»")
class TestCreateMaterialVideo:

    @allure.title("UI: Администратор создаёт материал БЗ типа «Видео»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_material_video(self, admin_page, api_client, env):
        kb_page = AdminKnowledgeBasePage(admin_page)
        video_name = f"Автотест видео {unique_suffix()}"
        material_id = None

        try:
            with allure.step("1. Открыть форму создания материала и выбрать тип «Видео»"):
                kb_page.open_material_create_form(env.ui_base_url)
                kb_page.select_material_type("Видео")

            with allure.step("2. Заполнить название, короткое описание и описание"):
                kb_page.fill_material_name(video_name)
                kb_page.fill_material_short_description("Короткое описание автотестового видео")
                kb_page.fill_material_description(
                    "Описание автотестового видео для проверки создания материала."
                )

            with allure.step("3. Указать длительность"):
                kb_page.set_material_duration(hours="0", minutes="1")

            with allure.step("4. Загрузить видеофайл"):
                kb_page.upload_material_content_file(TEST_DATA_DIR / "video.mp4", accept_hint=".mp4")

            with allure.step("5. Сохранить материал"):
                material_id = kb_page.save_material_and_get_id()
                logger.info(f"Видео-материал создан: ID={material_id}, name={video_name}")

            with allure.step("6. Проверить, что материал появился в списке материалов админки"):
                kb_page.expect_material_created(video_name)
        finally:
            with allure.step("7. Удалить материал через API"):
                if material_id is not None:
                    KnowledgeBaseEndpoint(api_client).delete_materials([material_id])
                    logger.info(f"Видео-материал удалён: ID={material_id}")
                else:
                    logger.warning("material_id не получен — удалять через API нечего")
