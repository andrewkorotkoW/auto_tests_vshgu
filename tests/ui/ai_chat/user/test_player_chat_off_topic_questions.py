"""ПМИ, шаги 28-29: вопрос не по теме курса («Какая столица Австралии?») и вопрос про сам
тест/задание («Помоги решить тест») — контракт идентичен контекстному вопросу (тот же
POST /llm-chat/{id}, docs/ai_chat_recon.md, 2.2), поэтому проверяется только факт получения
ответа и его сохранение в истории чата — точный текст ответа (отказ/формулировка) ИИ
недетерминирован и фиксируется только ручным кейсом, не автотестом.
"""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.login_page import LoginPage
from ui.pages.player_ai_chat_page import PlayerAiChatPage
from ui.pages.user_sidebar_page import UserSidebarPage

ANSWER_WAIT_TIMEOUT = 120000


@allure.feature("Чат с ИИ в курсах")
@allure.story("Плеер слушателя: вопрос не по теме / о самом тесте")
class TestPlayerChatOffTopicQuestions:

    @allure.title("Автотест_Плеер курса: вопрос «{question}» → ответ получен и записан в историю")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.ai_chat
    @pytest.mark.parametrize(
        "question",
        ["Какая столица Австралии?", "Помоги решить тест"],
        ids=["off_topic", "about_test"],
    )
    def test_question_answered_and_saved_to_history(
        self, page, env, prepared_user, tincan_with_ai_chat, tincan_endpoint, open_course_player, question
    ):
        allure.dynamic.parameter("question", question)
        content_id = tincan_with_ai_chat["id"]

        with allure.step("1. Подготовить слушателя и назначить курс в инд. обучение"):
            user = prepared_user()
            tincan_endpoint.assign_activities([content_id], [user["id"]])

        with allure.step("2. Войти слушателем, открыть плеер курса и чат"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
            UserSidebarPage(page).dismiss_popups()
            player_page = open_course_player(page, tincan_with_ai_chat["name"])
            chat_page = PlayerAiChatPage(player_page)
            chat_page.open_chat()

        with allure.step(f"3. Задать вопрос: «{question}»"):
            chat_page.ask(question)
            expect(chat_page.question_messages).to_have_count(1, timeout=10000)

        with allure.step(f"4. Дождаться ответа (до {ANSWER_WAIT_TIMEOUT // 1000} с) — текст не проверяется"):
            chat_page.wait_for_answer(1, timeout=ANSWER_WAIT_TIMEOUT)
            assert chat_page.last_answer_text(), "Ответ пришёл пустым"

        with allure.step("5. Вопрос и ответ сохранены в истории панели чата"):
            expect(chat_page.question_messages).to_have_count(1)
            expect(chat_page.answer_messages).to_have_count(1)
            assert question in (chat_page.question_messages.first.text_content() or "")
