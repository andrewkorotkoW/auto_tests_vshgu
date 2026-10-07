"""ПМИ, шаг 13: перетаскивание неподдерживаемого формата (xlsx) в зону загрузки —
page.dispatch_event('drop', {dataTransfer}), как указано в плане миссии. Сообщение об
ошибке — снэкбар .v-snack (селектор не был снят разведкой заранее, найден живым прогоном
при подготовке этого теста): «Ошибка <имя файла>: Данный формат не поддерживается».
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.admin_activity_ai_chat_page import AdminActivityAiChatPage

UNSUPPORTED_XLSX = "test_data/practical_task_additional_document.xlsx"


@allure.feature("Чат с ИИ в курсах")
@allure.story("Загрузка файлов через UI")
class TestAiChatDropUnsupportedFormat:

    @allure.title("Автотест_Перетаскивание XLSX в зону загрузки → «Данный формат не поддерживается»")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_drop_unsupported_format_rejected(self, admin_page, env, created_tincan):
        with allure.step("1. Создать курс, открыть карточку, включить переключатель"):
            course = created_tincan()
            content_id = course["id"]
            ai_chat_page = AdminActivityAiChatPage(admin_page)
            ai_chat_page.open_card(env.ui_base_url, content_id)
            ai_chat_page.toggle_switch()

        with allure.step("2. Перетащить xlsx в дропзону (drag'n'drop через DataTransfer)"):
            ai_chat_page.drop_unsupported_file(UNSUPPORTED_XLSX)

        with allure.step("3. Снэкбар с сообщением «Данный формат не поддерживается»"):
            snack = admin_page.locator(".v-snack:has-text('Данный формат не поддерживается')")
            expect(snack).to_be_visible(timeout=15000)

        with allure.step("4. Файл не попал в список загруженных"):
            assert ai_chat_page.file_rows.count() == 0
