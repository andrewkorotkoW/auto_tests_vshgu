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
from utils.logger import logger


@allure.feature("База знаний UI")
@allure.story("Создание статьи и проверка в UI пользователя")
class TestCreateArticleAndVerifyInUserUi:

    @allure.title("UI: Администратор создаёт статью в базе знаний, слушатель видит её в «Базе знаний»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_create_article_and_verify_in_user_ui(self, admin_page, user_page, api_client, env):
        kb_page = AdminKnowledgeBasePage(admin_page)
        article_name = f"Автотест статья {unique_suffix()}"
        short_description = "Короткое описание автотестовой статьи"
        article_text = "Текст автотестовой статьи для проверки отображения в UI пользователя."
        material_id = None

        try:
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
                logger.info(f"Статья создана: ID={material_id}, name={article_name}")

            with allure.step("5. Проверить, что статья появилась в списке материалов админки"):
                kb_page.expect_material_created(article_name)

            with allure.step("6. Открыть «Базу знаний» под пользователем"):
                user_kb_page = UserKnowledgeBasePage(user_page)
                user_kb_page.open(env.ui_base_url)

            with allure.step("7. Найти созданную статью через поиск и открыть её"):
                user_kb_page.search(article_name)
                user_page.wait_for_timeout(3000)
                for attempt in range(6):
                    found = user_kb_page.material_card(article_name).count() > 0
                    if found:
                        break
                    logger.info(f"Материал ещё не найден поиском, попытка {attempt + 1}/6, повтор через 5с")
                    user_page.wait_for_timeout(5000)
                    user_kb_page.search(article_name)
                    user_page.wait_for_timeout(3000)
                user_page.screenshot(path="/tmp/kb_debug_search.png", full_page=True)
                user_kb_page.open_material(article_name)

            with allure.step("8. Проверить заголовок статьи на странице материала"):
                user_kb_page.expect_material_title_visible(article_name)
        finally:
            with allure.step("9. Удалить статью через API"):
                if material_id is not None:
                    KnowledgeBaseEndpoint(api_client).delete_materials([material_id])
                    logger.info(f"Статья удалена: ID={material_id}")
                else:
                    logger.warning("material_id не получен — удалять через API нечего")
