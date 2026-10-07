"""Админка (global) → «База знаний → Материалы»: создание статьи через редактор,
затем проверка отображения статьи в UI пользователя (страница «База знаний»).

Перенос test_02_admin_create_article_material.py коллеги (репозиторий lms,
feature/my-tests, см. report.md разд. 2) — там сценарий проверял только сохранение
в списке материалов админки; здесь добавлена проверка в UI слушателя (через готовую
авторизованную сессию user_page, без ручного логина формой) и teardown через API.
"""
import allure
import pytest

from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage
from ui.pages.user_knowledge_base_page import UserKnowledgeBasePage


@allure.feature("База знаний UI")
@allure.story("Создание статьи и проверка в UI пользователя")
class TestCreateArticleAndVerifyInUserUi:

    @allure.title("UI: Администратор создаёт статью в базе знаний, слушатель видит её в «Базе знаний»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_article_and_verify_in_user_ui(
        self, admin_page, user_page, api_client, env, register_knowledge_base_material
    ):
        kb_page = AdminKnowledgeBasePage(admin_page)
        article_name = f"Автотест статья {unique_suffix()}"
        short_description = "Короткое описание автотестовой статьи"
        article_text = "Текст автотестовой статьи для проверки отображения в UI пользователя."

        with allure.step("1. Открыть форму создания материала в админке"):
            kb_page.open_material_create_form(env.ui_base_url)

        with allure.step("2. Выбрать тип материала «Статья»"):
            kb_page.select_material_type_article()

        with allure.step("3. Заполнить название, короткое описание и текст статьи"):
            kb_page.fill_material_name(article_name)
            kb_page.fill_material_short_description(short_description)
            kb_page.fill_article_text(article_text)

        with allure.step("4. Сохранить статью"):
            material_id = kb_page.save_material_and_get_id()
            register_knowledge_base_material(material_id)

        with allure.step("5. Опубликовать статью (по умолчанию создаётся скрытой — is_visible=false)"):
            KnowledgeBaseEndpoint(api_client).toggle_visibility(material_id, is_visible=True)

        with allure.step("6. Проверить, что статья появилась в списке материалов админки"):
            kb_page.expect_material_created(article_name)

        with allure.step("7. Открыть «Базу знаний» под пользователем"):
            user_kb_page = UserKnowledgeBasePage(user_page)
            user_kb_page.open(env.ui_base_url)

        with allure.step("8. Найти созданную статью через поиск и открыть её"):
            user_kb_page.open_material(article_name)

        with allure.step("9. Проверить заголовок статьи на странице материала"):
            user_kb_page.expect_material_title_visible(article_name)
