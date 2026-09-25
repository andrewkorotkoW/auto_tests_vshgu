"""Админка (global) → «База знаний → Материалы»: создание материала типа «Файл».

Перенос test_05_admin_create_file_material.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: Page Object вместо локаторов в тесте,
teardown через API вместо cleanup_manager.
"""
from pathlib import Path

import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage

TEST_DATA_DIR = Path(__file__).resolve().parents[3] / "test_data"


@allure.feature("База знаний UI")
@allure.story("Админка: создание материала «Файл»")
class TestCreateMaterialFile:

    @allure.title("UI: Администратор создаёт материал БЗ типа «Файл»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_material_file(self, admin_page, env, register_knowledge_base_material):
        kb_page = AdminKnowledgeBasePage(admin_page)
        file_name = f"Автотест файл {unique_suffix()}"

        with allure.step("1. Открыть форму создания материала и выбрать тип «Файл»"):
            kb_page.open_material_create_form(env.ui_base_url)
            kb_page.select_material_type("Файл")

        with allure.step("2. Заполнить название, короткое описание и описание"):
            kb_page.fill_material_name(file_name)
            kb_page.fill_material_short_description("Короткое описание автотестового файла")
            kb_page.fill_material_description(
                "Описание автотестового файла для проверки создания материала."
            )

        with allure.step("3. Загрузить файл"):
            kb_page.upload_material_content_file(TEST_DATA_DIR / "certificat.pdf", accept_hint=".pdf")

        with allure.step("4. Сохранить материал"):
            material_id = kb_page.save_material_and_get_id()
            register_knowledge_base_material(material_id)

        with allure.step("5. Проверить, что материал появился в списке материалов админки"):
            kb_page.expect_material_created(file_name)
