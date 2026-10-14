"""UI: пользователь создаёт обращение в «Техподдержка» (/support) через форму, видит его
в списке обращений и своё сообщение в открытой переписке.

Список обращений (виджет vue-advanced-chat) подгружается постранично и не отсортирован
по дате создания (см. докстрины TicketsPage.ticket_titles/ticket_row) — на общем
тестовом аккаунте develop с историей обращений свежесозданное почти никогда не попадает
в первую отрисованную порцию, поэтому список приходится докручивать до появления строки.
Поиск по тикетам (плейсхолдер «Поиск тикетов») в разведке оказался клиентским фильтром
только уже загруженных строк — не делает отдельный запрос и не помогает найти ещё не
подгруженную строку, поэтому не используется.

Текст обращения генерируется без "_": рендер переписки (markdown) трактует "_..._" как
курсив и вырезает подчёркивания несимметрично (зависит от их чётности в строке) — с
текстом по умолчанию (он включает title с "Автотест_обращение_master_<suffix>") результат
предсказать сравнением строк нельзя (см. README §13, кандидат в дефект)."""
import allure
import pytest
from playwright.sync_api import expect

from api.helpers.data_generator import generate_ticket_payload
from ui.pages.tickets_page import TicketsPage
from utils.logger import logger

CATEGORY = "Тип обращения №1"


@allure.feature("Техподдержка UI")
@allure.story("Пользователь создаёт обращение")
class TestUserCreatesTicket:

    @allure.title("Пользователь создаёт обращение через форму, видит его в списке и своё сообщение в переписке")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.e2e
    def test_user_creates_ticket_and_sees_it(self, user_page, env, tickets_endpoint):
        payload = generate_ticket_payload(text="Автотест текст обращения для проверки переписки")
        title = payload["title"]
        text = payload["text"]
        ticket_id = None

        try:
            tickets_page = TicketsPage(user_page)

            with allure.step("1. Открыть «Техподдержка»"):
                tickets_page.open(env.ui_base_url)

            with allure.step("2. Создать обращение через форму"):
                tickets_page.create_ticket(title, text, CATEGORY)

            with allure.step("3. Найти обращение через API (для надёжного teardown и id)"):
                found = tickets_endpoint.find_by_title(title)
                assert found is not None, "Обращение, созданное через форму, не найдено через my-tickets"
                ticket_id = found["id"]

            with allure.step("4. Обращение появляется в списке (докручиваем до появления строки)"):
                row = tickets_page.ticket_row(title)
                for _ in range(60):
                    if row.count() > 0 and row.is_visible():
                        break
                    tickets_page.tickets_list.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                    user_page.wait_for_timeout(700)
                expect(row).to_be_visible(timeout=8000)

            with allure.step("5. Открыть переписку — своё сообщение видно"):
                tickets_page.open_ticket(title)
                messages = tickets_page.message_texts()
                assert text in messages, f"Исходное сообщение не найдено в переписке: {messages}"
        finally:
            if ticket_id is not None:
                try:
                    tickets_endpoint.close(ticket_id)
                except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
                    logger.warning(f"Не удалось закрыть обращение {ticket_id} в teardown: {exc}")
