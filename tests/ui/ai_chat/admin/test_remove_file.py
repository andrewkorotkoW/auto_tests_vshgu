"""ПМИ, шаги 14, 16, 17: корзина у файла (с модалкой подтверждения) удаляет файл;
удаление всех документов → подпись «Файлы контекста пока не загружены…»; значок
«Чат с ИИ» в таблице активити при этом остаётся — он привязан к переключателю
(is_llm_chat_enabled), а не к наличию документов (факт 29.09, docs/ai_chat_recon.md, 1.8).
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_activities_page import AdminActivitiesPage
from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("Удаление файлов")
class TestAiChatRemoveFile:

    @allure.title("Автотест_Корзина удаляет файл; без документов — «Файлы контекста пока не загружены», значок остаётся")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_remove_last_file_keeps_icon(self, admin_page, env, tincan_with_ai_chat):
        content_id = tincan_with_ai_chat["id"]
        name = tincan_with_ai_chat["name"]
        file_name = list(tincan_with_ai_chat["knowledge"]["knowledge"]["files"].values())[0]

        ai_chat_page = AdminActivityAiChatPage(admin_page)
        activities_page = AdminActivitiesPage(admin_page)

        with allure.step("1. Открыть карточку — файл и история видны"):
            ai_chat_page.open_card(env.ui_base_url, content_id)
            assert ai_chat_page.file_row_by_name(file_name).is_visible(timeout=15000)
            assert ai_chat_page.history_block.is_visible(timeout=15000)

        with allure.step("2. Корзина → модалка подтверждения → «Удалить»"):
            ai_chat_page.remove_file(file_name)

        with allure.step("3. Файл пропал из списка, видна подпись «Файлы контекста пока не загружены…»"):
            expect(ai_chat_page.file_row_by_name(file_name)).to_have_count(0, timeout=15000)
            assert ai_chat_page.empty_state.is_visible(timeout=15000)
            # «Файлы контекста пока не загружены.» — первая фраза пустого состояния
            # (.activity-details-ai-chat-files__empty); вторая, в .../__empty-note —
            # «Без загруженного контекста чат не отображается слушателям.»
            empty_state_text = ai_chat_page.empty_state.text_content() or ""
            assert "Файлы контекста пока не загружены" in empty_state_text, empty_state_text

        with allure.step("4. Значок «Чат с ИИ» в таблице активити остаётся (привязан к переключателю, не к файлам)"):
            activities_page.open_list(env.ui_base_url)
            activities_page.search(name)
            row = activities_page.row_by_name(name)
            row.wait_for(state="visible", timeout=15000)
            ai_chat_page.expect_icon_visible(row)
