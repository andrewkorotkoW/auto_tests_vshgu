"""Админка (global) → «База знаний → Материалы»: создание материала типа «Курс»
поверх уже существующего курса Tincan.

Перенос test_06_admin_create_course_material.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: курс создаётся через API
(фикстура created_tincan вместо загрузки архива через UI-хелпер course_prepare_api),
Page Object вместо локаторов в тесте, teardown через API вместо cleanup_manager.
"""
import allure
import pytest

from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage


@allure.feature("База знаний UI")
@allure.story("Админка: создание материала «Курс»")
class TestCreateMaterialCourse:

    @allure.title("UI: Администратор создаёт материал БЗ типа «Курс» поверх курса Tincan")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_material_course(self, admin_page, api_client, env, created_tincan, tincan_endpoint):
        kb_page = AdminKnowledgeBasePage(admin_page)

        with allure.step("1. Подготовить курс Tincan через API"):
            tincan = created_tincan(archive_uuid=tincan_endpoint.upload_archive("test_data/course_tincan.zip"))
            course_name = tincan["name"]

        with allure.step("2. Открыть форму создания материала и выбрать тип «Курс»"):
            kb_page.open_material_create_form(env.ui_base_url)
            kb_page.select_material_type("Курс")

        with allure.step("3. Выбрать подготовленный курс"):
            kb_page.select_material_course(course_name)

        with allure.step("4. Сохранить материал"):
            material_id = kb_page.save_material_and_get_id()

        with allure.step("5. Проверить, что материал появился в списке материалов админки"):
            kb_page.expect_material_created(course_name)
