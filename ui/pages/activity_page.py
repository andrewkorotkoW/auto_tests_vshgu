from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage
from config.settings import settings
from utils.logger import logger


class ActivityPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def start_external_activity(self, program_name: str):
        """Открыть внешнюю активити (Игровая сессия)."""
        sidebar = UserSidebarPage(self.page)
        # dismiss_popups сам ждёт «Пройти обучение»/шаг тура с поллингом и закрывает всё по
        # кругу (cookie-баннер после тура включительно) — отдельные _start_tour_if_present и
        # complete_program_onboarding здесь были три лишних ожидания по таймауту (82 с шага).
        sidebar.dismiss_popups()
        program_title = self.page.locator(f"text={program_name}").first
        expect(program_title).to_be_visible(timeout=settings.UI_TIMEOUT)
        goto_btn = self.page.locator("button:has-text('Перейти к программе'), a:has-text('Перейти к программе')").first
        self.click_and_wait(goto_btn if goto_btn.count() > 0 else program_title, force=True)
        self.complete_program_onboarding()
        start_btn = self.page.locator("span:has-text('Начать')").first
        self.click_and_wait(self.page.locator("text=Игровая сессия").first, wait_for=start_btn)
        self.click_and_wait(start_btn, force=True)
        self.wait_loaded()

    def _start_tour_if_present(self):
        """Клик по «Пройти обучение» на первом для пользователя показе тура.

        dismiss_popups()/pass_onboarding() не всегда успевают поймать эту сплэш-кнопку,
        если тур рендерится с задержкой после закрытия анкеты «данные о себе»
        (is_visible() внутри pass_onboarding без поллинга) — здесь ждём через expect
        (с реальным поллингом), а не is_visible()."""
        start_btn = self.page.locator("button:has-text('Пройти обучение')").first
        try:
            expect(start_btn).to_be_visible(timeout=5000)
            start_btn.click(force=True)
            logger.info("Тур: «Пройти обучение»")
        except Exception:
            pass

    def complete_program_onboarding(self):
        """Карусель онбординга (Далее → Завершить) — делегирует в UserSidebarPage.pass_onboarding,
        которая дожидается реального исчезновения тёмного оверлея тура (не только кнопки),
        иначе за оверлеем остаётся демо-заглушка вместо реального списка программ."""
        UserSidebarPage(self.page).pass_onboarding()

    # ── МТС Линк: плеер записи в «Результатах активности» (часть 11) ────────────────
    # Функциональности ещё нет ни на одной ветке (docs/missions/2026-09-30_tz2026_mts_link.md,
    # docs/test_cases/mts_link/12_recording.md). «Результаты активности» как отдельный
    # узел карты продукта не выделены (см. tests/product_map.yml) — судя по остальным
    # методам этого класса, запись должна открываться там же, где слушатель завершает
    # мероприятие («Моё обучение» → активити). Разведки в браузере в этой среде нет.
    # TODO: уточнить после появления ветки — каждый локатор.

    def recording_player(self):
        return self.page.locator("[data-qa='mts-link-recording-player']")

    def is_recording_player_visible(self) -> bool:
        return self.recording_player().is_visible(timeout=settings.UI_TIMEOUT)

    def play_recording_to_end(self) -> None:
        """Досмотреть запись до конца — часть 11, раздел «Зачёт посещения по записи»."""
        player = self.recording_player()
        expect(player).to_be_visible(timeout=settings.UI_TIMEOUT)
        player.click(timeout=settings.UI_TIMEOUT)
        finished_marker = self.page.locator("[data-qa='mts-link-recording-finished']")
        expect(finished_marker).to_be_visible(timeout=settings.UI_TIMEOUT * 6)