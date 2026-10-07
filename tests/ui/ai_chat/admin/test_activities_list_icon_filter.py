"""ПМИ, шаги 4, 15, 19: значок «Чат с ИИ» в таблице активити отсутствует до настройки чата
и появляется после (привязан к is_llm_chat_enabled, не к content_type — проверено
параметризацией tincan|scorm, docs/ai_chat_recon.md, 1.8); фильтр «Курсы с чатом ИИ»
(filters[is_llm_chat_enabled]) возвращает только активити с чатом.
"""
import allure
import pytest

from ui.pages.admin_activities_page import AdminActivitiesPage
from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage

SOUPS_DOCX = "test_data/llm/soups.docx"


@allure.feature("Чат с ИИ в курсах")
@allure.story("Список активити: значок и фильтр")
class TestAiChatActivitiesListIconFilter:

    @allure.title("Автотест_Значок «Чат с ИИ» в таблице и фильтр «Курсы с чатом ИИ» ({content_type})")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    @pytest.mark.parametrize("content_type", ["tincan", "scorm"])
    def test_icon_and_filter(self, admin_page, env, llm_chat_endpoint, course_factory, unique_llm_file, content_type):
        allure.dynamic.parameter("content_type", content_type)

        with allure.step(f"1. Создать активити типа {content_type} без чата с ИИ"):
            course = course_factory(content_type)
            content_id = course["id"]
            name = course["name"]

        activities_page = AdminActivitiesPage(admin_page)
        ai_chat_page = AdminActivityAiChatPage(admin_page)

        with allure.step("2. Список активити: поиск по названию — значка нет"):
            activities_page.open_list(env.ui_base_url)
            activities_page.search(name)
            row = activities_page.row_by_name(name)
            row.wait_for(state="visible", timeout=15000)
            ai_chat_page.expect_icon_hidden(row)

        with allure.step("3. Включить чат с ИИ и загрузить файл (API) — дождаться обработки"):
            uploaded = llm_chat_endpoint.upload_files([unique_llm_file(SOUPS_DOCX)])
            storage_uuid = uploaded[0]["uuid"]
            llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
            llm_chat_endpoint.wait_processed(content_id)

        with allure.step("4. Список активити: поиск по названию — значок появился"):
            activities_page.open_list(env.ui_base_url)
            activities_page.search(name)
            row = activities_page.row_by_name(name)
            row.wait_for(state="visible", timeout=15000)
            ai_chat_page.expect_icon_visible(row)

        with allure.step("5. Включить фильтр «Курсы с чатом ИИ» → активити есть в выдаче"):
            admin_page.locator("text=Фильтр").first.click(timeout=5000)
            # Page object AdminActivityAiChatPage.enable_ai_chat_filter() кликает raw
            # input без force=True — перехватывается .v-input--selection-controls__ripple
            # той же Vuetify-анимации (page object не менялся, обход — в тесте).
            checkbox = ai_chat_page.ai_chat_filter_checkbox
            checkbox.wait_for(state="visible", timeout=15000)
            checkbox.click(force=True, timeout=5000)
            apply_button = admin_page.locator("button:has-text('Применить')").first
            apply_button.wait_for(state="visible", timeout=15000)
            apply_button.click(force=True, timeout=5000)
            activities_page.search(name)
            expect_row = activities_page.row_by_name(name)
            expect_row.wait_for(state="visible", timeout=15000)
