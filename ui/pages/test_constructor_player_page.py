"""Плеер «Конструктора тестов и опросов» на стороне слушателя (/testing/player) —
прохождение теста (вопрос за вопросом, доп. вопросы по теме после неверного ответа)
и опроса/АОС с последовательностью вопросов по ответам (группы вопросов целиком на
одной странице, ветвление по ответу, пропуск необязательной группы).

Перенос src/ui/pages/test_constructor_player_page.py коллеги (ветка
origin/feature/test-constructor-autotests, ConstructorPlayerPage) в наш Page Object:
без allure.step внутри методов (см. ui/pages/test_constructor_admin_page.py), без
ручного time.monotonic()-поллинга (playwright expect() на объединённый локатор через
Locator.or_ вместо цикла), закрытие анкеты «данные о себе»/тура/cookie-баннера/плашки
техработ — через UserSidebarPage.dismiss_popups (как и на остальных страницах
слушателя, см. ui/pages/aos_page.py), а не своим кодом.
"""
import re

from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class ConstructorPlayerPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    # ── Навигация ────────────────────────────────────────────────────────

    def open_by_content_id(self, ui_base_url: str, content_id: int) -> None:
        """Открыть прохождение теста/опроса слушателем напрямую по content_id —
        доступно без индивидуального назначения (в отличие от АОС, у которой
        публичная ссылка обязательна, см. open_by_launch_url)."""
        self.page.goto(f"{ui_base_url.rstrip('/')}/testing/player?test={content_id}")
        expect(self.page).to_have_url(re.compile(rf".*/testing/player/{content_id}/.*"), timeout=30000)
        UserSidebarPage(self.page).dismiss_popups()

    def open_by_launch_url(self, launch_url: str, content_id: int) -> None:
        """Открыть тест/опрос/АОС по ссылке запуска — индивидуальное назначение
        теста слушателю или публичная ссылка АОС потока (см.
        api.endpoints.aos.AosEndpoint.public_link)."""
        self.page.goto(launch_url)
        expect(self.page).to_have_url(re.compile(rf".*/testing/player/{content_id}/.*"), timeout=30000)
        UserSidebarPage(self.page).dismiss_popups()

    # ── Старт ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Нажать «Начать» на вступительном слайде — общий для теста/опроса/АОС."""
        start_btn = self.page.get_by_role("button", name="Начать").first
        expect(start_btn).to_be_visible(timeout=30000)
        start_btn.click()

    # ── Тест: один вопрос на экране ─────────────────────────────────────

    def assert_question_visible(self, question_text: str) -> None:
        expect(self.page.get_by_text(question_text, exact=True)).to_be_visible(timeout=30000)

    def assert_question_not_visible(self, question_text: str) -> None:
        expect(self.page.get_by_text(question_text, exact=True)).not_to_be_visible(timeout=10000)

    def answer_question(self, answer_text: str) -> None:
        """Выбрать вариант ответа (single choice) и подтвердить."""
        self.page.get_by_text(answer_text, exact=True).click()
        self.page.get_by_role("button", name="Ответить").click()

    def go_to_next_question(self) -> None:
        next_btn = self.page.get_by_role("button", name="Следующий вопрос")
        expect(next_btn).to_be_visible(timeout=30000)
        next_btn.click()

    def finish_test(self) -> None:
        """Завершить тест после ответа на последний вопрос — итоговый экран с
        результатом («Ваш результат:»)."""
        finish_btn = self.page.get_by_role("button", name="Завершить").first
        expect(finish_btn).to_be_visible(timeout=30000)
        finish_btn.click()
        self._confirm_finish_dialog_if_present()
        expect(self.page.get_by_text("Ваш результат:", exact=False)).to_be_visible(timeout=30000)

    def assert_success_result_visible(self) -> None:
        expect(self.page.get_by_text("Успешное прохождение", exact=True)).to_be_visible(timeout=30000)
        expect(
            self.page.get_by_text("Поздравляем, вы успешно завершили тестирование!", exact=True)
        ).to_be_visible(timeout=30000)
        expect(self.page.get_by_text("Ваш результат:", exact=False)).to_be_visible(timeout=30000)

    # ── Опрос/АОС: группа вопросов целиком на экране ────────────────────

    def answer_current_group(self, answer_text: str = None) -> bool:
        """Ответить на текущую группу вопросов опроса/АОС и подтвердить.

        Покрывает оба варианта группы: одиночный вопрос с вариантом ответа
        (answer_text — выбранный вариант, определяет переход по последовательности,
        см. настройку «Переход к группе» в ConstructorAdminPage.add_single_question_to_group)
        и группа АОС из нескольких вопросов разных типов (шкала 1-10 — берём первый
        вариант, комментарий, чекбоксы — отмечаем первый).

        Возвращает True, если после ответа есть переход к следующей группе, False —
        если группа была последней (сразу видна кнопка «Завершить»)."""
        page = self.page

        for comment in page.locator(".input-word-answer textarea").all():
            if comment.is_visible():
                comment.fill("Комментарий автотеста")

        for statement in page.locator(".likert-scale__statement").all():
            if not statement.is_visible():
                continue
            buttons = statement.locator(".likert-scale__btn")
            if buttons.count():
                buttons.first.click()

        for checkbox in page.locator(".multi-answer__checkbox").all():
            if checkbox.is_visible():
                checkbox.click()
                break

        if answer_text is not None:
            page.get_by_text(answer_text, exact=True).click()

        answer_btn = page.get_by_role("button", name="Ответить")
        expect(answer_btn).to_be_enabled(timeout=30000)
        answer_btn.click()

        next_group_btn = page.get_by_role("button", name="Перейти к следующей группе")
        finish_btn = page.get_by_role("button", name="Завершить").first
        expect(next_group_btn.or_(finish_btn)).to_be_visible(timeout=30000)

        if next_group_btn.is_visible(timeout=500):
            next_group_btn.click()
            return True
        return False

    def answer_groups_until_finish(self, max_groups: int = 10) -> None:
        """Доответить оставшиеся группы опроса/АОС до появления «Завершить» —
        для сценариев без проверок конкретных ответов по пути."""
        finish_btn = self.page.get_by_role("button", name="Завершить").first
        for _ in range(max_groups):
            if finish_btn.is_visible(timeout=1000):
                return
            self.answer_current_group()
        expect(finish_btn).to_be_visible(timeout=30000)

    def finish_survey(self) -> None:
        """Завершить опрос/АОС после ответа на последнюю группу — финальный экран
        «Спасибо за прохождение опроса!»."""
        finish_btn = self.page.get_by_role("button", name="Завершить").first
        expect(finish_btn).to_be_visible(timeout=30000)
        finish_btn.click()
        self._confirm_finish_dialog_if_present()
        expect(self.page.get_by_text("Спасибо за прохождение опроса!", exact=True)).to_be_visible(timeout=30000)

    # ── Общее ────────────────────────────────────────────────────────────

    def finish_result_screen(self) -> None:
        """Закрыть итоговый экран (результат теста или благодарность опроса/АОС)."""
        finish_btn = self.page.get_by_role("button", name="Завершить")
        expect(finish_btn).to_be_visible(timeout=30000)
        finish_btn.click()

    def assert_no_error_snackbar_visible(self) -> None:
        error_snackbar = self.page.locator(".v-snackbar, [role='alert']").filter(
            has_text=re.compile(r"Ошибка|ошибка|Не удалось|не удалось|Произошла|произошла|Неправильное прохождение")
        )
        expect(error_snackbar).not_to_be_visible(timeout=5000)

    def _confirm_finish_dialog_if_present(self) -> None:
        dialog = self.page.get_by_role("dialog")
        if dialog.is_visible(timeout=3000):
            dialog.get_by_role("button", name="Да").click()
