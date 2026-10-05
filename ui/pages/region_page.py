from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from config.settings import settings


class RegionPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_user_menu(self):
        """Нажать на ФИО в хедере."""
        self.click_and_wait(self.page.locator("[data-onboarding-step='user-menu']").first, force=True)

    def select_region(self, region_name: str = "Москва"):
        # Тройной клик для выделения
        region_input = self.page.locator("#input-v-0")
        region_input.click(click_count=3, force=True)
        # Очистить
        self.page.keyboard.press("Backspace")
        # Ввести
        self.page.keyboard.type(region_name, delay=100)
        # Выбрать из списка
        option = self.wait_visible(f"[role='option']:has-text('{region_name}')")
        option.click(force=True)

    def select_municipality(self, municipality_name: str = "Южный округ"):
        """Выбрать муниципалитет."""
        municipality_input = self.page.locator("#input-v-3")
        municipality_input.click()
        municipality_input.fill(municipality_name)
        option = self.wait_visible(f"text={municipality_name}")
        option.click()
        self.wait_loaded()

    def accept_agreement(self):
        """Отметить чекбокс согласия на обработку ПД."""
        checkbox = self.page.locator("#checkbox-v-6")
        if not checkbox.is_checked():
            checkbox.check()
        expect(checkbox).to_be_checked(timeout=settings.UI_TIMEOUT)

    def click_continue(self):
        """Нажать кнопку Отправить."""
        self.click_and_wait(self.page.locator("button:has-text('Отправить')").first)

    def go_to_lk(self):
        """Перейти в Личный кабинет обучающегося."""
        self.click_and_wait(
            self.page.locator("div.v-list-item-title:has-text('Личный кабинет обучающегося')").first, force=True
        )

