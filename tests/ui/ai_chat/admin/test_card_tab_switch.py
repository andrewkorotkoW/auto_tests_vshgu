"""ПМИ «Чат с ИИ_курсы_ПМИ_v2», шаги 5-8: карточка активити открывается на вкладке
«Чат с ИИ» (?i=1), переключатель изначально выключен, клик включает его локально
(блок «Контекст обсуждения») — но флаг не сохраняется на бэкенде, пока не загружен
первый файл (docs/ai_chat_recon.md, 1.2; docs/plans/2026-10-07_ai_chat_pmi_mission.md).
"""
import allure
import pytest

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("Карточка активити: вкладка и переключатель")
class TestAiChatCardTabSwitch:

    @allure.title("Автотест_Вкладка «Чат с ИИ»: выключенный переключатель, включение не сохраняется без файла")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_tab_and_switch_without_file(self, admin_page, env, llm_chat_endpoint, created_tincan):
        with allure.step("1. Создать курс Tincan"):
            course = created_tincan()
            content_id = course["id"]

        with allure.step("2. API: у новой активити чат не настроен"):
            assert llm_chat_endpoint.get(content_id) is None

        with allure.step("3. Открыть карточку активити сразу на вкладке «Чат с ИИ» (?i=1)"):
            ai_chat_page = AdminActivityAiChatPage(admin_page)
            ai_chat_page.open_card(env.ui_base_url, content_id)

        with allure.step("4. Заголовок и описание секции видны"):
            assert ai_chat_page.settings_title.is_visible(timeout=15000)
            assert ai_chat_page.settings_description.is_visible(timeout=15000)

        with allure.step("5. Переключатель изначально выключен"):
            assert not ai_chat_page.is_switch_checked()

        with allure.step("6. Клик по переключателю → появляется блок «Контекст обсуждения»"):
            ai_chat_page.toggle_switch()
            assert ai_chat_page.context_block.is_visible(timeout=15000)

        with allure.step("7. API: флаг не сохранён на бэкенде без первого файла (факт 29.09)"):
            assert llm_chat_endpoint.get(content_id) is None
