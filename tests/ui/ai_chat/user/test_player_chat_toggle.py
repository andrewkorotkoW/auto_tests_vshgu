"""ПМИ, шаг 23: в плеере курса, назначенного слушателю (индивидуальное обучение), видна
кнопка чата с ИИ и подсказка при наведении (docs/ai_chat_recon.md, 2.1, 3.3).
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.login_page import LoginPage
from ui.pages.player_ai_chat_page import PlayerAiChatPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("Плеер слушателя: кнопка чата")
class TestPlayerChatToggle:

    @allure.title("Автотест_Плеер курса (инд. обучение): кнопка чата с ИИ и подсказка видны")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    def test_chat_button_visible_in_player(
        self, page, env, prepared_user, tincan_with_ai_chat, tincan_endpoint, open_course_player
    ):
        content_id = tincan_with_ai_chat["id"]

        with allure.step("1. Подготовить слушателя и назначить курс в инд. обучение"):
            user = prepared_user()
            tincan_endpoint.assign_activities([content_id], [user["id"]])

        with allure.step("2. Войти слушателем"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            UserSidebarPage(page).dismiss_popups()

        with allure.step("3. Открыть плеер курса через индивидуальное обучение"):
            player_page = open_course_player(page, tincan_with_ai_chat["name"])

        with allure.step("4. Кнопка чата с ИИ видна, подсказка при наведении показывает ожидаемый текст"):
            chat_page = PlayerAiChatPage(player_page)
            expect(chat_page.toggle_button).to_be_visible(timeout=20000)
            chat_page.toggle_button.hover()
            expect(chat_page.toggle_tooltip).to_be_visible(timeout=10000)
            assert "Обсудить материалы курса с ИИ" in (chat_page.toggle_tooltip.text_content() or "")
