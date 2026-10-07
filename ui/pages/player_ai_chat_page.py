"""Плеер курса слушателя → чат с ИИ (button.player-chat-toggle, aside.player-chat) —
локаторы и контракт сняты разведкой, см. docs/ai_chat_recon.md (разделы 2, 3.3)."""
from typing import Optional

from playwright.sync_api import Page, Locator, expect
from ui.pages.base_page import BasePage


class PlayerAiChatPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    # ── Кнопка / панель ──────────────────────────────────────────────────

    @property
    def toggle_button(self) -> Locator:
        """Рендерится в самом плеере, вне #iframe с содержимым xAPI (docs/ai_chat_recon.md, 2.1)."""
        return self.page.locator("button.player-chat-toggle")

    @property
    def toggle_tooltip(self) -> Locator:
        return self.page.locator(".player-chat-toggle__tooltip")

    @property
    def panel(self) -> Locator:
        return self.page.locator("aside.player-chat")

    def open_chat(self) -> None:
        expect(self.toggle_button).to_be_visible(timeout=15000)
        self.toggle_button.click(timeout=5000)
        expect(self.panel).to_be_visible(timeout=15000)

    def close_chat(self) -> None:
        close_button = self.page.locator(".player-chat__close")
        expect(close_button).to_be_visible(timeout=15000)
        close_button.click(timeout=5000)
        expect(self.panel).to_be_hidden(timeout=15000)

    def expect_toggle_hidden(self) -> None:
        """Курс с выключенным чатом или без документов контекста — кнопка остаётся в DOM,
        но скрыта (docs/plans/2026-10-07_ai_chat_pmi_mission.md, шаги 32-33: to_be_hidden,
        не to_have_count(0))."""
        expect(self.toggle_button).to_be_hidden(timeout=15000)

    @property
    def empty_state(self) -> Locator:
        return self.page.locator(".player-chat__empty")

    @property
    def empty_state_text(self) -> Locator:
        return self.page.locator(".player-chat__empty-text")

    # ── Вопрос / ответ ───────────────────────────────────────────────────

    @property
    def input_field(self) -> Locator:
        return self.page.locator("textarea.player-chat__input")

    @property
    def send_button(self) -> Locator:
        return self.page.locator("button.player-chat__send")

    def ask(self, question: str) -> None:
        expect(self.input_field).to_be_visible(timeout=15000)
        self.input_field.fill(question, timeout=5000)
        expect(self.send_button).to_be_enabled(timeout=15000)
        self.send_button.click(timeout=5000)

    def is_input_disabled(self) -> bool:
        return self.input_field.is_disabled()

    @property
    def date_dividers(self) -> Locator:
        return self.page.locator(".player-chat__date")

    @property
    def question_messages(self) -> Locator:
        return self.page.locator(".player-chat__message.player-chat__message_question")

    @property
    def answer_messages(self) -> Locator:
        return self.page.locator(".player-chat__message.player-chat__message_answer")

    def wait_for_answer(self, expected_count: int, timeout: int = 120000) -> None:
        """Ждёт появления N-го ответа. По плану — до 120 с (ответы ИИ недетерминированы
        и небыстры), по факту разведки ~5 с (docs/ai_chat_recon.md, 2.3) — таймаут остаётся
        защитой от выбросов, не ожидаемым типичным временем."""
        expect(self.answer_messages).to_have_count(expected_count, timeout=timeout)

    def last_answer_text(self) -> str:
        return self.answer_messages.last.locator(".player-chat__text").text_content().strip()

    def last_answer_time(self) -> str:
        return self.answer_messages.last.locator(".player-chat__time").text_content().strip()

    # ── Оценка (звёзды + комментарий) ────────────────────────────────────

    @property
    def rating_block(self) -> Locator:
        """Скрыт до первого ответа (docs/ai_chat_recon.md, 3.3)."""
        return self.page.locator(".player-chat__rating")

    def star(self, value: int) -> Locator:
        return self.page.locator(f'button.player-chat__star[data-value="{value}"]')

    @property
    def comment_field(self) -> Locator:
        """Скрыт, пока звезда не выбрана."""
        return self.page.locator("textarea.player-chat__comment")

    @property
    def rating_send_button(self) -> Locator:
        return self.page.locator(".player-chat__rating-send")

    @property
    def rating_cancel_button(self) -> Locator:
        return self.page.locator(".player-chat__rating-cancel")

    @property
    def rating_done_block(self) -> Locator:
        return self.page.locator(".player-chat__rating-done")

    @property
    def rating_edit_button(self) -> Locator:
        return self.page.locator(".player-chat__rating-edit")

    def rate(self, value: int, comment: Optional[str] = None) -> None:
        expect(self.rating_block).to_be_visible(timeout=15000)
        self.star(value).click(timeout=5000)
        if comment:
            expect(self.comment_field).to_be_visible(timeout=15000)
            self.comment_field.fill(comment, timeout=5000)
        expect(self.rating_send_button).to_be_enabled(timeout=15000)
        self.rating_send_button.click(timeout=5000)
        expect(self.rating_done_block).to_be_visible(timeout=15000)

    def cancel_rating(self) -> None:
        self.rating_cancel_button.click(timeout=5000)

    def reopen_rating(self) -> None:
        """После отправки оценки — «Оценить работу чата» (docs/ai_chat_recon.md, 3.3)."""
        expect(self.rating_edit_button).to_be_visible(timeout=15000)
        self.rating_edit_button.click(timeout=5000)
