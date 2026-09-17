import allure
import pytest
import time
from ui.pages.login_page import LoginPage
from config.settings import settings
from utils.logger import logger
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.endpoints.users import UsersEndpoint


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

        # ========== UI: Проверка отображения ==========
        with allure.step("4. Логин"):
            login_page = LoginPage(page)
            login_page.login(user["email"], user["password"])
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)
            page.screenshot(path="allure-results/kb_ui_01_login.png")
            allure.attach.file("allure-results/kb_ui_01_login.png", "Логин", allure.attachment_type.PNG)

        with allure.step("5. Онбординг"):
            try:
                start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                if start_btn.is_visible(timeout=3000):
                    start_btn.click(force=True)
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                    else:
                        break
            except:
                pass
            page.screenshot(path="allure-results/kb_ui_02_onboarding.png")
            allure.attach.file("allure-results/kb_ui_02_onboarding.png", "Онбординг", allure.attachment_type.PNG)

        with allure.step("6. Открыть вкладку «База знаний» и пройти онбординг"):
            # Ищем и кликаем по вкладке "База знаний"
            kb_tab = page.locator("text=База знаний")
            if kb_tab.count() == 0:
                kb_tab = page.locator("a:has-text('База знаний'), span:has-text('База знаний')").first
            assert kb_tab.count() > 0, "Вкладка 'База знаний' не найдена"
            kb_tab.first.click(force=True)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

            # Онбординг внутри Базы знаний (такие же шаги, как в основном)
            try:
                start_btn = page.locator("span:has-text('Пройти обучение'), span:has-text('Начать обучение')").first
                if start_btn.is_visible(timeout=3000):
                    start_btn.click(force=True)
                for _ in range(15):
                    btn = page.locator('[data-qa="onboarding-popup-next"]')
                    if btn.is_visible(timeout=2000):
                        btn.click(force=True)
                    else:
                        break
            except:
                pass

            page.screenshot(path="allure-results/kb_ui_03_kb_page.png")
            allure.attach.file("allure-results/kb_ui_03_kb_page.png", "Страница Базы знаний",
                               allure.attachment_type.PNG)
            logger.info("Вкладка 'База знаний' открыта, онбординг пройден")
            catalog_btn = page.locator("button.v-btn:has(span:has-text('Каталог'))").first
            if catalog_btn.count() == 0:
                catalog_btn = page.locator("button:has-text('Каталог')").first
            assert catalog_btn.count() > 0, "Кнопка 'Каталог' не найдена"
            catalog_btn.click(force=True)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

            page.screenshot(path="allure-results/kb_ui_03_kb_catalog.png")
            allure.attach.file("allure-results/kb_ui_03_kb_catalog.png", "Каталог Базы знаний",
                               allure.attachment_type.PNG)
            logger.info("Каталог Базы знаний открыт")


            # Выбираем тег в каталоге (например, "Антикоррупционная политика", который соответствует тегу id=8)
            tag_link = page.locator("a.catalog-menu__list-item:has-text('Антикоррупционная политика')")
            if tag_link.count() == 0:
                # Если точного совпадения нет, пробуем любой пункт меню
                tag_link = page.locator("a.catalog-menu__list-item").first
            assert tag_link.count() > 0, "Пункт каталога не найден"
            tag_link.first.click(force=True)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

            page.screenshot(path="allure-results/kb_ui_03_kb_catalog_filtered.png")
            allure.attach.file("allure-results/kb_ui_03_kb_catalog_filtered.png", "Каталог отфильтрован", allure.attachment_type.PNG)
            logger.info("Тег в каталоге выбран")

        with allure.step("7. Найти и открыть созданный материал"):
            # Ищем карточку по name_client (внешнему имени)
            tincan_name_client = f"{tincan_payload['data']['attributes']['name_client']}"
            material_card = page.locator(f"span.library-card__name:has-text('{tincan_name_client}')").first
            if material_card.count() == 0:
                material_card = page.locator(f"text={tincan_name_client}").first
            assert material_card.count() > 0, f"Материал '{tincan_name_client}' не найден в каталоге"
            material_card.click(force=True)
            page.wait_for_load_state("networkidle", timeout=settings.UI_TIMEOUT)

            page.screenshot(path="allure-results/kb_ui_04_material_opened.png")
            allure.attach.file("allure-results/kb_ui_04_material_opened.png", "Страница материала",
                               allure.attachment_type.PNG)
            logger.info(f"Материал '{tincan_name_client}' открыт")


        with allure.step("8. Проверить элементы на странице материала"):
            # Проверка заголовка (h2 с названием)
            title = page.locator(f"h2.material-header__title:has-text('{tincan_name_client}')")
            assert title.is_visible(timeout=5000), "Заголовок материала не отображается"
            logger.info(f"Заголовок '{tincan_name_client}' отображается")

            # Проверка тега (ссылка с названием тега)
            tag = page.locator("a.material-info__tag:has-text('Антикоррупционная политика')")
            assert tag.is_visible(timeout=3000), "Тег материала не отображается"
            logger.info("Тег 'Антикоррупционная политика' отображается")

            # Проверка раздела "Авторы"
            authors_title = page.locator("span.material-core__section-title:has-text('Авторы')")
            assert authors_title.is_visible(timeout=3000), "Раздел 'Авторы' не отображается"
            logger.info("Раздел 'Авторы' отображается")

            # Проверка имени автора
            author_name = page.locator("span.material-content__author-name:has-text('AQA')")
            assert author_name.is_visible(timeout=3000), "Имя автора 'AQA' не отображается"
            logger.info("Автор 'AQA' отображается")

            # Проверка кнопки "Изучать"
            study_btn = page.locator("button.v-btn:has(span:has-text('Изучать'))")
            assert study_btn.is_visible(timeout=3000), "Кнопка 'Изучать' не отображается"
            logger.info("Кнопка 'Изучать' отображается")

            page.screenshot(path="allure-results/kb_ui_05_elements_checked.png")
            allure.attach.file("allure-results/kb_ui_05_elements_checked.png", "Элементы проверены", allure.attachment_type.PNG)

            with allure.step("9. Нажать «Изучать» и дождаться кнопки «Приступить к изучению»"):
                study_btn = page.locator("button.v-btn:has(span:has-text('Изучать'))")
                assert study_btn.is_visible(timeout=5000), "Кнопка 'Изучать' не отображается"

                # Кликаем «Изучать»
                study_btn.click(force=True)

                # Ждём появления кнопки «Приступить к изучению»
                page.wait_for_selector("button.v-btn:has(span:has-text('Приступить к изучению'))", timeout=15000)

                page.screenshot(path="allure-results/kb_ui_06_ready_to_start.png")
                allure.attach.file("allure-results/kb_ui_06_ready_to_start.png",
                                   "Кнопка «Приступить к изучению» появилась", allure.attachment_type.PNG)
                logger.info("Кнопка «Приступить к изучению» появилась")

                page.wait_for_selector("button.v-btn:has(span:has-text('Приступить к изучению'))", timeout=15000)
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