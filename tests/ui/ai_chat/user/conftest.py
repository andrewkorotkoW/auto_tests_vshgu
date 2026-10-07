"""Локальные фикстуры для tests/ui/ai_chat/user — открытие плеера курса слушателем.

Путь «поток» не используется: у page object'а TincanPage уже задокументирован xfail на
навигацию в потоке (tests/ui/courses/tincan/stream/test_user_tincan_flow.py), а разведка
подтвердила, что кнопка чата рендерится тем же компонентом плеера независимо от способа
назначения — поэтому курс назначается в индивидуальное обучение (assign_activities), как
и в разведке (docs/ai_chat_recon.md, примечание к шагу 23/31).
"""
import pytest
from playwright.sync_api import Page, expect

from ui.pages.user_sidebar_page import UserSidebarPage


@pytest.fixture
def open_course_player():
    """Открывает плеер курса через индивидуальное обучение, возвращает страницу плеера
    (саму внешнюю страницу плеера, без захода в #iframe — кнопка чата рендерится вне
    него и не зависит от того, загрузился ли сам SCORM/xAPI-пакет, docs/ai_chat_recon.md,
    2.1).

    Не переиспользует TincanPage.start_tincan_individual() напрямую: у него
    `self.page.context.expect_page(timeout=5000)` вокруг клика «Начать» — при текущей
    загрузке стенда открытие новой вкладки плеера иногда занимает больше 5 с, из-за чего
    try/except в page object тихо откатывается на старую (дэшборд) страницу, и все
    дальнейшие проверки идут не по той странице (кандидат в дефект page object,
    см. отчёт; сам page object не менялся). Здесь — тот же алгоритм навигации
    (повторяет публичные шаги TincanPage до клика «Начать»), но с увеличенным таймаутом
    ожидания новой вкладки."""
    def _open(page: Page, course_name: str) -> Page:
        sidebar = UserSidebarPage(page)
        banner = page.locator("text=Индивидуальное обучение").first
        expect(banner).to_be_visible(timeout=30000)
        banner.click(force=True)
        page.wait_for_timeout(1500)
        sidebar.dismiss_popups()
        tab = page.locator("xpath=//span[normalize-space()='Курсы и тесты']").first
        expect(tab).to_be_visible(timeout=15000)
        tab.click(force=True)
        page.wait_for_timeout(1000)
        sidebar.dismiss_popups()
        course_card = page.get_by_text(course_name, exact=False).first
        expect(course_card).to_be_visible(timeout=30000)
        print(f"DEBUG course_card found for '{course_name}', url={page.url}")
        course_card.click(force=True)
        sidebar.pass_onboarding()
        print(f"DEBUG after onboarding, url={page.url}")

        start_btn = page.locator("button.v-btn:has-text('Начать')").first
        # Кнопка видна сразу после перехода на карточку курса, но какое-то время остаётся
        # disabled (бледно-голубая, клик по ней ничего не делает) — ждём to_be_enabled,
        # не просто to_be_visible.
        expect(start_btn).to_be_enabled(timeout=30000)
        try:
            with page.context.expect_page(timeout=15000) as new_page_info:
                start_btn.click(force=True)
            player_page = new_page_info.value
            print(f"DEBUG new tab opened url={player_page.url}")
        except Exception as exc:  # noqa: BLE001 — «Начать» мог открыть плеер в текущей вкладке
            player_page = page
            print(f"DEBUG no new tab ({exc!r}), url={page.url}")
        player_page.wait_for_load_state("networkidle", timeout=30000)
        return player_page
    return _open
