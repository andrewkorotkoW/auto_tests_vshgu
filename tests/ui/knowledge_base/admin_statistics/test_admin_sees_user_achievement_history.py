"""Админка → «База знаний → Достижения → История»: администратор видит полученное
пользователем достижение.

Перенос test_01_admin_sees_user_achievement_history.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: материал/достижение готовятся через API
(KnowledgeBaseEndpoint), слушатель проходит материал через API от своего имени
(user_session), Page Object вместо локаторов в тесте, teardown через API вместо
cleanup_manager.
"""
import allure
import pytest

from api.client import ApiClient
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.helpers.data_generator import unique_suffix
from ui.pages.admin_knowledge_base_page import AdminKnowledgeBasePage
from utils.logger import logger


@allure.feature("База знаний UI")
@allure.story("Админка: история полученных достижений")
class TestAdminSeesUserAchievementHistory:

    @allure.title("UI: Администратор видит полученное пользователем достижение в истории")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_admin_sees_user_achievement_history(self, admin_page, api_client, env, user_session):
        kb_endpoint = KnowledgeBaseEndpoint(api_client)
        user_api_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        user_kb_endpoint = KnowledgeBaseEndpoint(user_api_client)

        suffix = unique_suffix()
        article_name = f"Автотест_Материал_история_{suffix}"
        achievement_name = f"Автотест_Достижение_история_{suffix}"
        achievement_description = "Автотестовое достижение: проверка истории полученных достижений"
        article_text = "".join(
            f"<p>Абзац {number}. Автотестовая статья для проверки истории достижений.</p>"
            for number in range(1, 21)
        )

        material_id = None
        achievement_id = None
        try:
            with allure.step("1. Подготовить статью через API"):
                # is_visible=True передаётся напрямую в payload создания (по умолчанию в
                # create_article_material) — toggle-visibility здесь не нужен: это чистый
                # тоггл вне зависимости от значения в теле, и вызов на уже видимом материале
                # скрыл бы его обратно (найдено при переносе).
                material = kb_endpoint.create_article_material(name=article_name, article_text=article_text)
                material_id = material["id"]
                logger.info(f"Статья создана: ID={material_id}, name={article_name}")

            with allure.step("2. Подготовить достижение «1 статья» через API"):
                achievement = kb_endpoint.create_material_count_achievement(
                    name=achievement_name, description=achievement_description,
                    material_type="article", count=1,
                )
                achievement_id = achievement["id"]
                logger.info(f"Достижение создано: ID={achievement_id}, name={achievement_name}")

            with allure.step("3. Слушатель изучает статью через API"):
                user_kb_endpoint.pass_material_via_api(material_id)

            with allure.step("4. Получить ФИО слушателя и дождаться начисления достижения"):
                me = user_api_client.get("/auth/me").json()["data"]["attributes"]
                full_name = f"{me['surname']} {me['name']} {me['patronymic']}"
                kb_endpoint.wait_user_achievement(full_name, achievement_name)

            admin_page_obj = AdminKnowledgeBasePage(admin_page)
            with allure.step("5. Открыть историю полученных достижений в админке"):
                admin_page_obj.open_achievement_history(env.ui_base_url)

            with allure.step(f"6. Найти историю по ФИО пользователя «{full_name}»"):
                admin_page_obj.search_achievement_history_by_user(full_name)

            with allure.step("7. Проверить запись о полученном достижении в истории"):
                admin_page_obj.expect_user_achievement_in_history(full_name, achievement_name)
        finally:
            with allure.step("8. Удалить достижение и материал через API"):
                if achievement_id is not None:
                    kb_endpoint.delete_achievement(achievement_id)
                    logger.info(f"Достижение удалено: ID={achievement_id}")
                if material_id is not None:
                    kb_endpoint.delete_materials([material_id])
                    logger.info(f"Статья удалена: ID={material_id}")
