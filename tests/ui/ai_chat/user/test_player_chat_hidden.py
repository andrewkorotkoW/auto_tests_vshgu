"""ПМИ, шаги 32-33: курс с выключенным чатом с ИИ и курс с удалёнными документами контекста
(после удаления всех файлов, но с чатом, остающимся включённым — факт 29.09,
docs/ai_chat_recon.md, 1.8) — в обоих случаях кнопка чата в плеере слушателя скрыта
(to_be_hidden, не to_have_count(0) — кнопка остаётся в DOM, PlayerAiChatPage.expect_toggle_hidden).
"""
import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.player_ai_chat_page import PlayerAiChatPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Чат с ИИ в курсах")
@allure.story("Плеер слушателя: кнопка чата скрыта без контекста")
class TestPlayerChatHidden:

    @allure.title("Автотест_Плеер курса ({case}): кнопка чата с ИИ скрыта")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    @pytest.mark.parametrize(
        "fixture_name, case",
        [
            ("tincan_with_ai_chat_disabled", "чат выключен"),
            ("tincan_with_ai_chat_no_docs", "документы контекста удалены"),
        ],
    )
    def test_chat_button_hidden(
        self, request, page, env, prepared_user, tincan_endpoint, open_course_player, fixture_name, case
    ):
        allure.dynamic.parameter("case", case)
        course = request.getfixturevalue(fixture_name)
        content_id = course["id"]

        with allure.step("1. Подготовить слушателя и назначить курс в инд. обучение"):
            user = prepared_user()
            tincan_endpoint.assign_activities([content_id], [user["id"]])

        with allure.step("2. Войти слушателем и открыть плеер курса"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            UserSidebarPage(page).dismiss_popups()
            player_page = open_course_player(page, course["name"])

        with allure.step(f"3. Кнопка чата с ИИ скрыта ({case})"):
            chat_page = PlayerAiChatPage(player_page)
            chat_page.expect_toggle_hidden()
