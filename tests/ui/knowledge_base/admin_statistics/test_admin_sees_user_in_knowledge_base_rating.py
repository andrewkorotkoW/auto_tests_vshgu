"""Админка → «База знаний → Рейтинг»: администратор видит пользователя, изучившего материал,
в рейтинге Базы знаний.

Перенос test_02_admin_sees_user_in_knowledge_base_rating.py коллеги (репозиторий lms,
feature/dashboard-autotests) на нашу архитектуру: материал готовится через API
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
@allure.story("Админка: рейтинг Базы знаний")
class TestAdminSeesUserInKnowledgeBaseRating:

    @allure.title("UI: Администратор видит пользователя в рейтинге Базы знаний")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.knowledge_base
    def test_admin_sees_user_in_knowledge_base_rating(self, admin_page, api_client, env, user_session):
        kb_endpoint = KnowledgeBaseEndpoint(api_client)
        user_api_client = ApiClient(session=user_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
        user_kb_endpoint = KnowledgeBaseEndpoint(user_api_client)

        article_name = f"Автотест_Материал_рейтинг_{unique_suffix()}"
        article_text = "".join(
            f"<p>Абзац {number}. Автотестовая статья для проверки рейтинга Базы знаний.</p>"
            for number in range(1, 21)
        )

        material_id = None
        try:
            with allure.step("1. Получить ФИО слушателя и текущую статистику (учётка общая, счётчики не с нуля)"):
                me = user_api_client.get("/auth/me").json()["data"]["attributes"]
                full_name = f"{me['surname']} {me['name']} {me['patronymic']}"
                baseline = next(iter(kb_endpoint.get_material_statistics(full_name)), {})
                baseline_article = int(baseline.get("article", 0))
                baseline_total = int(baseline.get("total", 0))

            with allure.step("2. Подготовить статью через API"):
                # is_visible=True — напрямую в payload создания, toggle-visibility не нужен
                # (это чистый тоггл, вызов на уже видимом материале скрыл бы его обратно).
                material = kb_endpoint.create_article_material(name=article_name, article_text=article_text)
                material_id = material["id"]
                logger.info(f"Статья создана: ID={material_id}, name={article_name}")

            with allure.step("3. Слушатель изучает статью через API"):
                user_kb_endpoint.pass_material_via_api(material_id)

            with allure.step("4. Дождаться обновления статистики (article/total выросли относительно baseline)"):
                # Таймаут больше значения по умолчанию (120с): на develop статистика
                # рейтинга иногда пересчитывается с задержкой при частых прогонах подряд —
                # тот же класс лага, что и в статистике курсов (см. память
                # dashboards_test_stats_lag_and_instability), кандидат в дефекты стенда.
                kb_endpoint.wait_material_statistics(
                    full_name,
                    expected={"article": baseline_article + 1, "total": baseline_total + 1},
                    timeout=180,
                )

            admin_page_obj = AdminKnowledgeBasePage(admin_page)
            with allure.step("5. Открыть рейтинг Базы знаний в админке"):
                admin_page_obj.open_knowledge_base_rating(env.ui_base_url)

            with allure.step(f"6. Найти пользователя «{full_name}» в рейтинге"):
                admin_page_obj.search_rating_by_user(full_name)

            with allure.step("7. Проверить, что пользователь отображается в рейтинге"):
                admin_page_obj.expect_user_in_rating(full_name)
        finally:
            with allure.step("8. Удалить материал через API"):
                if material_id is not None:
                    kb_endpoint.delete_materials([material_id])
                    logger.info(f"Статья удалена: ID={material_id}")
