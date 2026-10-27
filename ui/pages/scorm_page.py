"""Курс SCORM глазами слушателя: карточка курса в «Индивидуальном обучении» и в модуле
программы, кнопка «Начать»/«Продолжить»/«Повторить», плеер `/xapi/drivers/scorm` и сам пакет
Articulate Storyline (`test_data/test_lms_scorm_2004.zip`, 2 слайда: текст → вопрос «Сколько углов у
треугольника?» с ответами «3»/«шланг», SUBMIT → Results «Your Score: 100%»).

Разведка — стенд vshgu2-2420-filters, 27.10.2026 (scratchpad scorm2420/recon*.py):
- «Начать» открывает новую вкладку `<portal>/xapi/drivers/scorm?xAPILaunchKey=<jwt>`; пакет грузится
  в `iframe#iframe` (`/static/content/<uuid>/<hash>/index_lms.html`), внутри — Storyline без
  дополнительных вложенных фреймов для контента (вложенные `lms/*.html` — служебные);
- драйвер LMS выставляет SCORM 2004 API (`window.API_1484_11`) и переводит вызовы пакета в xAPI:
  `POST <portal>/xAPI/statements` (initialized+launched при открытии, responded на ответ,
  passed+completed на SUBMIT, suspended при закрытии) и `PUT /xAPI/activities/state` — всё это
  попадает в OpenLRS (Agent = id пользователя LMS);
- после прохождения кнопка в карточке меняется на «Повторить», «Продолжить» — у начатого курса;
  в программе курс в модуле открыт сразу (`/education/program/<uuid>/module/<id>/activities`).
Кнопки Storyline — `button.cs-button` с текстом NEXT/PREV/SUBMIT/Continue; у пакета есть скрытая
«SUBMIT ALL», поэтому искать строго по имени (`get_by_role(..., exact=True)`). Варианты ответа —
`[role=radio][aria-label=<текст>]`."""
import json
import re

from playwright.sync_api import FrameLocator, Locator, Page, expect

from config.settings import settings
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

PLAYER_URL_RE = re.compile(r"/xapi/drivers/scorm")


class ScormCoursePage(BasePage):
    """Карточка курса SCORM у слушателя (инд. обучение или модуль программы)."""

    ACTION_BUTTON = "button.v-btn:has-text('Начать'), button.v-btn:has-text('Продолжить'), button.v-btn:has-text('Повторить')"

    def open_individual_course(self, course_name: str) -> None:
        """«Моё обучение» → баннер «Индивидуальное обучение» → вкладка «Курсы и тесты» → карточка
        курса (тот же маршрут, что у TincanPage.start_tincan_individual)."""
        sidebar = UserSidebarPage(self.page)
        banner = self.page.locator("text=Индивидуальное обучение").first
        expect(banner).to_be_visible(timeout=settings.UI_TIMEOUT)
        banner.click(force=True)
        tab = self.page.locator("xpath=//span[normalize-space()='Курсы и тесты']").first
        expect(tab).to_be_visible(timeout=settings.UI_TIMEOUT)
        sidebar.dismiss_popups()
        tab.click(force=True)
        sidebar.dismiss_popups()
        self._open_card(course_name)

    def open_program_course(self, program_name: str, course_name: str) -> None:
        """«Моё обучение» → карточка программы → «Перейти к программе» → страница модуля
        (`/module/<id>/activities`, вкладка «Курсы и тесты» активна, карточка курса открыта)."""
        sidebar = UserSidebarPage(self.page)
        card_title = self.page.locator(f"text={program_name}").first
        expect(card_title).to_be_visible(timeout=settings.UI_TIMEOUT)
        goto_btn = self.page.locator("button:has-text('Перейти к программе'), a:has-text('Перейти к программе')").first
        (goto_btn if goto_btn.count() else card_title).click(force=True)
        sidebar.pass_onboarding()
        expect(self.page).to_have_url(re.compile(r"/education/program/"), timeout=settings.UI_TIMEOUT)
        tab = self.page.locator("xpath=//*[normalize-space()='Курсы и тесты']").first
        if tab.count() and tab.is_visible():
            tab.click(force=True)
        self._open_card(course_name)

    def _open_card(self, course_name: str) -> None:
        card = self.page.get_by_text(course_name, exact=False).first
        expect(card).to_be_visible(timeout=settings.UI_TIMEOUT)
        card.click(force=True)
        UserSidebarPage(self.page).pass_onboarding()
        expect(self.action_button).to_be_visible(timeout=settings.UI_TIMEOUT)

    @property
    def action_button(self) -> Locator:
        return self.page.locator(self.ACTION_BUTTON).first

    def action_button_text(self) -> str:
        return self.action_button.inner_text().strip()

    def details_text(self) -> str:
        details = self.page.locator(".details, [class*='details']").first
        return details.inner_text() if details.count() else self.page.locator("body").inner_text()

    def start(self) -> "StorylinePlayer":
        """Клик по «Начать»/«Продолжить»/«Повторить» → плеер в новой вкладке (если вкладка не
        открылась за 5 с — считаем, что плеер в текущей)."""
        try:
            with self.page.context.expect_page(timeout=5000) as page_info:
                self.action_button.click(force=True)
            player_page = page_info.value
        except Exception:  # noqa: BLE001 — плеер открылся в той же вкладке
            player_page = self.page
        player_page.wait_for_load_state("domcontentloaded", timeout=settings.UI_TIMEOUT)
        expect(player_page).to_have_url(PLAYER_URL_RE, timeout=settings.UI_TIMEOUT)
        return StorylinePlayer(player_page)

    def reload_card(self) -> None:
        """Обновить страницу карточки — статус/кнопка пересчитываются после закрытия плеера."""
        self.page.reload(wait_until="domcontentloaded")
        UserSidebarPage(self.page).dismiss_popups()
        expect(self.action_button).to_be_visible(timeout=settings.UI_TIMEOUT)


class StorylinePlayer:
    """Плеер SCORM (`/xapi/drivers/scorm`) с пакетом Storyline внутри `iframe#iframe`.
    С момента создания записывает xAPI-statements, которые драйвер шлёт в `POST /xAPI/statements`
    (`sent_statements`), — так прохождение проверяется на любом окружении, без доступа в OpenLRS."""

    def __init__(self, page: Page):
        self.page = page
        self.sent_statements: list = []
        self.page.on("request", self._capture_statement)

    def _capture_statement(self, request) -> None:
        if request.method != "POST" or not request.url.split("?")[0].endswith("/xAPI/statements"):
            return
        try:
            body = json.loads(request.post_data or "[]")
        except ValueError:
            return
        self.sent_statements.extend(body if isinstance(body, list) else [body])

    @property
    def sent_verbs(self) -> list:
        return [s.get("verb", {}).get("id", "").rsplit("/", 1)[-1] for s in self.sent_statements]

    def statement(self, verb: str) -> dict:
        return next((s for s in self.sent_statements if s.get("verb", {}).get("id", "").endswith("/" + verb)), {})

    @property
    def frame(self) -> FrameLocator:
        return self.page.frame_locator("#iframe")

    def _button(self, name: str) -> Locator:
        return self.frame.get_by_role("button", name=name, exact=True).first

    def wait_ready(self) -> None:
        """Пакет загружен: на первом слайде есть NEXT."""
        expect(self._button("NEXT")).to_be_visible(timeout=settings.UI_TIMEOUT * 4)

    def body_text(self) -> str:
        return self.frame.locator("body").inner_text()

    def next(self) -> None:
        self._button("NEXT").click()

    def choose(self, answer_text: str) -> None:
        """Вариант ответа на слайде-вопросе — `[role=radio]` с aria-label = текст ответа."""
        option = self.frame.locator(f"[role='radio'][aria-label='{answer_text}']").first
        expect(option).to_be_visible(timeout=settings.UI_TIMEOUT)
        option.click()

    def submit(self) -> None:
        self._button("SUBMIT").click()

    def continue_(self) -> None:
        """«Continue» в окне обратной связи после SUBMIT → слайд Results."""
        self._button("Continue").click()

    def pass_test_package(self, answer_text: str = "3") -> str:
        """Пройти test_lms_scorm_2004: NEXT → ответ → SUBMIT → Continue. Возвращает текст
        слайда Results («Your Score: 100%»)."""
        self.wait_ready()
        self.next()
        self.choose(answer_text)
        self.submit()
        self.continue_()
        # Текст слайдов Storyline — SVG <text>, не HTMLElement (inner_text у него падает), поэтому
        # ждём и читаем через body; процент дорисовывается анимацией позже заголовка «Your Score».
        body = self.frame.locator("body")
        # Между словами и числом Storyline вставляет символы нулевой ширины (U+200B) — пропускаем их.
        score_re = re.compile(r"Your[\s\u200b]*Score:?[\s\u200b]*(\d+)[\s\u200b]*%")
        expect(body).to_contain_text(score_re, timeout=settings.UI_TIMEOUT * 2)
        match = score_re.search(body.inner_text())
        text = f"Your Score: {match.group(1)}%" if match else "Your Score: ?"
        logger.info(f"Storyline results: {text}")
        return text

    def scorm_values(self) -> dict:
        """Значения модели SCORM 2004 из API драйвера (`window.API_1484_11`) — completion_status,
        success_status, score.raw/scaled."""
        return self.page.evaluate(
            """() => { const api = window.API_1484_11 || window.API; if (!api) return {};
                const get = k => { try { return api.GetValue(k); } catch (e) { return null; } };
                return { completion_status: get('cmi.completion_status'), success_status: get('cmi.success_status'),
                         score_raw: get('cmi.score.raw'), score_scaled: get('cmi.score.scaled'), exit: get('cmi.exit') }; }"""
        )

    def close(self) -> None:
        self.page.close()
