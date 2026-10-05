from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from config.settings import settings
from utils.logger import logger


class LpdPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def select_lpd_tab(self):
        """Выбрать вкладку «ЛПД» в списке активностей (инд. трек или программа)."""
        tab = self.page.locator("span.py-2:has-text('ЛПД')").first
        if tab.count() > 0 and tab.is_visible(timeout=3000):
            tab.click(force=True)
            return
        self.page.evaluate("""() => {
            const spans = document.querySelectorAll('span.py-2');
            for (const span of spans) {
                if (span.textContent.trim() === 'ЛПД') { span.click(); break; }
            }
        }""")
        logger.info("Вкладка 'ЛПД' выбрана")

    def open_by_name(self, lpd_name: str):
        """Дождаться и открыть карточку LPD с данным именем (после выбора вкладки ЛПД)."""
        item = self.page.locator(f"text={lpd_name}").first
        self.wait_visible(item, timeout=settings.UI_TIMEOUT)
        self.click_and_wait(item, force=True)
        logger.info(f"ЛПД '{lpd_name}' открыт")

    def open_individual_lpd(self, lpd_name: str):
        """Индивидуальное обучение → вкладка ЛПД → карточка lpd_name."""
        self.click_and_wait(self.page.locator("text=Индивидуальное обучение").first, force=True)
        self.complete_program_onboarding()
        self.select_lpd_tab()
        self.open_by_name(lpd_name)

    def open_program_lpd(self, program_name: str, lpd_name: str):
        """Программа program_name → вкладка ЛПД → карточка lpd_name."""
        self.click_and_wait(self.page.locator(f"text={program_name}").first, force=True)
        self.complete_program_onboarding()
        self.select_lpd_tab()
        self.open_by_name(lpd_name)

    def launch(self, button_text: str = "Начать"):
        """Кликнуть кнопку запуска LPD (Начать/Продолжить) и вернуть новую вкладку."""
        with self.page.context.expect_event("page", timeout=settings.UI_TIMEOUT) as event:
            self.page.locator(f"span:has-text('{button_text}')").first.click(force=True)
        new_page = event.value
        new_page.wait_for_load_state("networkidle")
        logger.info(f"Новая вкладка LPD: {new_page.url}")
        return new_page

    def wait_report_pending(self, timeout: int = None):
        """Проверить, что кнопка «Отчет формируется» видна и неактивна."""
        btn = self.page.locator("button:has-text('Отчет формируется')").first
        self.wait_visible(btn, timeout=timeout)
        assert btn.get_attribute("disabled") is not None, "Кнопка 'Отчет формируется' должна быть неактивна"
        return btn

    def wait_start_button(self, timeout: int = None):
        """Дождаться, что кнопка «Начать» снова видна (прогресс LPD сброшен)."""
        btn = self.page.locator("span[data-v-b1dcf706]:has-text('Начать')").first
        if btn.count() == 0:
            btn = self.page.locator("button.v-btn:has(span:has-text('Начать'))").first
        return self.wait_visible(btn, timeout=timeout)

    def start_lpd(self):
        """Открыть LPD через индивидуальное обучение."""
        self.click_and_wait("text=Индивидуальное обучение")
        self.complete_program_onboarding()
        self.click_and_wait("text=ЛПД")
        self.complete_program_onboarding()
        # Клик по первому LPD в списке
        lpd_item = self.page.locator("span:has-text('ЛПД'), .lpd-item, .content-item").first
        start_btn = self.page.locator("span:has-text('Начать')").first
        self.click_and_wait(lpd_item, wait_for=start_btn)
        start_btn.click()

    def start_stream_lpd(self, program_name: str):
        """Открыть LPD через программу (поток)."""
        self.click_and_wait(self.page.locator(f"span:has-text('{program_name}')").first)
        self.page.screenshot(path="allure-results/lpd_stream_inside.png")
        self.complete_program_onboarding()


    def complete_program_onboarding(self):
        """Пройти онбординг."""
        try:
            for _ in range(25):
                btn = self.page.locator('[data-qa="onboarding-popup-next"]')
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                else:
                    break
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
            logger.info("Онбординг пройден")
        except Exception as e:
            logger.info(f"Онбординг: {e}")