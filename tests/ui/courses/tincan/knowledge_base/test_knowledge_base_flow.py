import allure
import pytest
import time
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from config.settings import settings
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.endpoints.users import UsersEndpoint
from ui.pages.user_knowledge_base_page import UserKnowledgeBasePage


@allure.feature("Knowledge Base UI")
@allure.story("Full Flow: Create Course → Material → UI")
class TestKnowledgeBaseFlow:

    @allure.title("E2E Develop: Создание курса → материал в БЗ → UI: логин → база знаний")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.develop
    @pytest.mark.ui
    def test_create_course_and_view_in_ui(self, page, api_client, created_user):
        kb_ep = KnowledgeBaseEndpoint(api_client)
        tincan_ep = TincanEndpoint(api_client)

        # ========== API: Подготовка данных ==========
        with allure.step("1. Создать пользователя"):
            user = created_user()
            logger.info(f"Пользователь: ID={user['id']}, email={user['email']}")

        with allure.step("2. Загрузить обложку и архив, создать курс Tincan"):
            cover_uuid = tincan_ep.upload_cover()
            archive_uuid = tincan_ep.upload_archive()
            sub_uuid = tincan_ep.upload_sub_file()
            logger.info(f"Обложка: {cover_uuid}, архив: {archive_uuid}")

            from api.helpers.data_generator import generate_tincan_payload
            tincan_payload = generate_tincan_payload(
                archive_uuid=archive_uuid,
                cover_uuid=cover_uuid,
                sub_files_uuids=[sub_uuid]
            )
            tincan_data = tincan_ep.create(tincan_payload)
            content_id = tincan_data["id"]
            logger.info(f"Курс Tincan создан: content_id={content_id}")

        with allure.step("3. Создать материал в базе знаний"):
            from api.helpers.data_generator import generate_material_payload
            material_name = f"Автотест_Курс_{int(time.time() * 1000)}"
            material_payload = generate_material_payload(
                name=material_name,
                content_id=content_id,
                cover_uuid=cover_uuid
            )
            material_data = kb_ep.create_material(material_payload)
            material_id = material_data["id"]
            logger.info(f"Материал создан: ID={material_id}, name={material_name}")

            material_tag_id = material_payload["data"]["tags"][0]
            tags_by_id = {tag["id"]: tag["name"] for tag in kb_ep.list_tags()}
            material_tag_name = tags_by_id[material_tag_id]
            logger.info(f"Тег материала: ID={material_tag_id}, name={material_tag_name}")

        # ========== UI: Проверка отображения ==========
        tincan_name_client = tincan_payload["data"]["attributes"]["name_client"]

        with allure.step("4. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/kb_ui_01_login.png")
            allure.attach.file("allure-results/kb_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5-6. Открыть «Базу знаний» и найти созданный материал через поиск"):
            # UserKnowledgeBasePage открывает /library напрямую и закрывает анкету/cookie/онбординг
            # (сайдбар-клик и каталог+тег были нестабильны — тур на develop иногда блокирует переход).
            kb_page = UserKnowledgeBasePage(page)
            kb_page.open(settings.UI_BASE_URL)
            kb_page.sidebar.close_tour_dialog()
            page.screenshot(path="allure-results/kb_ui_02_onboarding.png")
            allure.attach.file("allure-results/kb_ui_02_onboarding.png", "База знаний открыта",
                               allure.attachment_type.PNG)

        with allure.step("7. Найти и открыть созданный материал"):
            # Серверный поиск фильтрует по внутреннему имени контента (tincan_data["name"],
            # без суффикса "_внешка") — по name_client (внешнему, с суффиксом) он не находит
            # ничего, хотя карточка в каталоге отображается именно с name_client.
            kb_page.open_material(tincan_data["attributes"]["name"])

            page.screenshot(path="allure-results/kb_ui_04_material_opened.png")
            allure.attach.file("allure-results/kb_ui_04_material_opened.png", "Страница материала",
                               allure.attachment_type.PNG)
            logger.info(f"Материал '{tincan_name_client}' открыт")


        with allure.step("8. Проверить элементы на странице материала"):
            # Проверка заголовка (h2 с названием) — страница материала рендерится медленно
            title = page.locator(f"h2.material-header__title:has-text('{tincan_name_client}')")
            expect(title).to_be_visible(timeout=45000)
            logger.info(f"Заголовок '{tincan_name_client}' отображается")

            # Проверка тега (ссылка с названием тега)
            tag = page.locator(f"a.material-info__tag:has-text('{material_tag_name}')")
            expect(tag).to_be_visible(timeout=15000)
            logger.info(f"Тег '{material_tag_name}' отображается")

            # Проверка раздела "Авторы"
            authors_title = page.locator("span.material-core__section-title:has-text('Авторы')")
            expect(authors_title).to_be_visible(timeout=15000)
            logger.info("Раздел 'Авторы' отображается")

            # Проверка имени автора
            author_name = page.locator("span.material-content__author-name:has-text('AQA')")
            expect(author_name).to_be_visible(timeout=15000)
            logger.info("Автор 'AQA' отображается")

            # Проверка кнопки "Приступить к изучению" (UI изменился: кнопки "Изучать"
            # с промежуточным шагом больше нет, материал сразу готов к запуску)
            study_btn = page.locator("button.v-btn:has(span:has-text('Приступить к изучению'))")
            expect(study_btn).to_be_visible(timeout=15000)
            logger.info("Кнопка 'Приступить к изучению' отображается")

            page.screenshot(path="allure-results/kb_ui_05_elements_checked.png")
            allure.attach.file("allure-results/kb_ui_05_elements_checked.png", "Элементы проверены", allure.attachment_type.PNG)

            with allure.step("9. Нажать «Приступить к изучению»"):
                page.evaluate("""
                                () => {
                                    const buttons = document.querySelectorAll('button.v-btn');
                                    for (const btn of buttons) {
                                        if (btn.textContent.includes('Приступить к изучению')) {
                                            btn.click();
                                            break;
                                        }
                                    }
                                }
                            """)
                page.wait_for_load_state("networkidle")

                page.screenshot(path="allure-results/kb_ui_06_course_loaded.png")
                allure.attach.file("allure-results/kb_ui_06_course_loaded.png", "Курс загружен",
                                   allure.attachment_type.PNG)
                logger.info(f"Курс загружен: URL={page.url}")


        # ========== Очистка ==========
        with allure.step("10. Очистка данных"):
            kb_ep.delete_materials([material_id])
            tincan_ep.delete(content_id)
            try:
                UsersEndpoint(api_client).delete(user["id"])
                logger.info(f"Пользователь {user['id']} удалён")
            except:
                logger.warning(f"Не удалось удалить пользователя {user['id']} (возможно, уже удалён)")
            logger.info("Очистка завершена")