"""Админка (global) → «База знаний → Достижения»: создание достижения с условием
«Количество материалов» и иконкой.

Перенос test_01_admin_create_achievement_material_count.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2) — там сценарий был без teardown; здесь
достижение помечается для удаления, если в api/endpoints/knowledge_base.py найдётся
подходящий метод (см. итоговое резюме — метода для achievements там нет, поэтому
запись остаётся в стенде осознанно).
"""
from pathlib import Path

import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage
from utils.logger import logger

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@allure.feature("База знаний UI")
@allure.story("Админка: создание достижения")
class TestCreateAchievement:

    @allure.title("UI: Администратор создаёт достижение «Количество материалов = 1 статья» с иконкой")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_achievement(self, admin_page, env):
        kb_page = AdminKnowledgeBasePage(admin_page)
        icon_path = TEST_DATA_DIR / "achievement_icon.png"

        with allure.step("1. Проверить, что файл иконки подготовлен"):
            assert icon_path.exists(), f"Файл иконки не найден: {icon_path}"
            assert icon_path.stat().st_size <= 200 * 1024, (
                f"Иконка больше 200 КБ: {icon_path.stat().st_size} байт"
            )

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
            kb_page.save_achievement()

        with allure.step("6. Проверить, что достижение появилось в списке созданных"):
            kb_page.expect_achievement_created(achievement_name)
            logger.info(f"Достижение создано в UI: name={achievement_name}")
