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

SOUPS_DOCX = "test_data/llm/soups.docx"


@pytest.fixture
def tincan_with_ai_chat(created_tincan, llm_chat_endpoint, unique_llm_file, tincan_endpoint):
    """Переопределяет общую фикстуру tests/ui/ai_chat/conftest.py для тестов слушателя:
    курс обязательно создаётся с архивом (tincan_endpoint.upload_archive(), дефолтный
    test_data/course_tincan.zip) и обложкой. Без архива кнопка «Начать» в карточке курса
    остаётся disabled (известный факт проекта — курс нельзя запустить без архива), и плеер
    никогда не открывается, из-за чего все тесты слушателя падали бы по таймауту на
    открытии плеера, а не по сути проверяемой функциональности."""
    cover_uuid = tincan_endpoint.upload_cover()
    archive_uuid = tincan_endpoint.upload_archive()
    tincan = created_tincan(archive_uuid=archive_uuid, cover_uuid=cover_uuid)
    content_id = tincan["id"]

    uploaded = llm_chat_endpoint.upload_files([unique_llm_file(SOUPS_DOCX)])
    storage_uuid = uploaded[0]["uuid"]
    llm_chat_endpoint.setup(content_id, [storage_uuid], is_enabled=1)
    knowledge = llm_chat_endpoint.wait_processed(content_id)

    return {
        "id": content_id,
        "name": tincan["name"],
        "attributes": tincan["attributes"],
        "storage_uuid": storage_uuid,
        "knowledge": knowledge,
    }


@pytest.fixture
def tincan_with_ai_chat_disabled(tincan_with_ai_chat, llm_chat_endpoint):
    """Тот же курс (с архивом, настроенным и обработанным чатом), но с выключенным
    переключателем (PATCH /content/{id}/llm-chat — is_llm_chat_enabled → false,
    docs/ai_chat_recon.md, 1.5) — для проверки, что кнопка чата скрыта в плеере."""
    llm_chat_endpoint.disable(tincan_with_ai_chat["id"])
    return tincan_with_ai_chat


@pytest.fixture
def tincan_with_ai_chat_no_docs(tincan_with_ai_chat, llm_chat_endpoint):
    """Тот же курс, но единственный файл контекста удалён (шаг 16/17 ПМИ) — переключатель
    остаётся включённым (факт 29.09, docs/ai_chat_recon.md, 1.8: значок в админке не
    зависит от документов), проверяется поведение кнопки чата в плеере без контекста."""
    llm_knowledge_uuid = tincan_with_ai_chat["knowledge"]["llm_knowledge_uuid"]
    storage_uuid = tincan_with_ai_chat["storage_uuid"]
    llm_chat_endpoint.remove_file(llm_knowledge_uuid, storage_uuid)
    return tincan_with_ai_chat


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
    ожидания новой вкладки.

    Кнопка на карточке курса — «Начать» при первом открытии и «Продолжить» при всех
    следующих (обнаружено живым прогоном 08.10.2026: тесты с повторным входом в один и
    тот же курс иначе зависают на to_be_enabled, не находя «Начать»)."""
    def _open(page: Page, course_name: str) -> Page:
        sidebar = UserSidebarPage(page)
        banner = page.locator("text=Индивидуальное обучение").first
        expect(banner).to_be_visible(timeout=30000)
        banner.click(force=True)
        # Раздел открылся, когда видна его вкладка; сами попапы/тур dismiss_popups ждёт сам.
        tab = page.locator("xpath=//span[normalize-space()='Курсы и тесты']").first
        expect(tab).to_be_visible(timeout=15000)
        sidebar.dismiss_popups()
        tab.click(force=True)
        sidebar.dismiss_popups()
        course_card = page.get_by_text(course_name, exact=False).first
        expect(course_card).to_be_visible(timeout=30000)
        course_card.click(force=True)
        sidebar.pass_onboarding()

        start_btn = page.locator("button.v-btn:has-text('Начать'), button.v-btn:has-text('Продолжить')").first
        # Кнопка видна сразу после перехода на карточку курса, но какое-то время остаётся
        # disabled (бледно-голубая, клик по ней ничего не делает) — ждём to_be_enabled,
        # не просто to_be_visible.
        expect(start_btn).to_be_enabled(timeout=30000)
        try:
            with page.context.expect_page(timeout=15000) as new_page_info:
                start_btn.click(force=True)
            player_page = new_page_info.value
        except Exception:  # noqa: BLE001 — «Начать» мог открыть плеер в текущей вкладке
            player_page = page
        player_page.wait_for_load_state("domcontentloaded", timeout=30000)
        return player_page
    return _open
