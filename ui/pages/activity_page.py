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
        sidebar.dismiss_popups()
        self._start_tour_if_present()
        self.complete_program_onboarding()
        sidebar.dismiss_popups()  # cookie-баннер может переотрисоваться после тура
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