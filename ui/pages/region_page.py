from playwright.sync_api import Page
from ui.pages.base_page import BasePage


class RegionPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def open_user_menu(self):
        """Нажать на ФИО в хедере."""
        self.page.locator("[data-onboarding-step='user-menu']").first.click(force=True)
        self.page.wait_for_timeout(500)

    def select_region(self, region_name: str = "Москва"):
        # Тройной клик для выделения
        self.page.locator("#input-v-0").click(click_count=3, force=True)
        self.page.wait_for_timeout(300)
        # Очистить
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(300)
        # Ввести
        self.page.keyboard.type(region_name, delay=100)
        self.page.wait_for_timeout(1000)
        # Выбрать из списка
        self.page.locator(f"[role='option']:has-text('{region_name}')").first.click(force=True)

    def select_municipality(self, municipality_name: str = "Южный округ"):
        """Выбрать муниципалитет."""
        self.page.locator("#input-v-3").click()
        self.page.wait_for_timeout(500)
        self.page.locator("#input-v-3").fill(municipality_name)
        self.page.wait_for_timeout(1000)
        self.page.locator(f"text={municipality_name}").first.click()
        self.page.wait_for_timeout(500)

    def accept_agreement(self):
        """Отметить чекбокс согласия на обработку ПД."""
        checkbox = self.page.locator("#checkbox-v-6")
        if not checkbox.is_checked():
            checkbox.check()
        self.page.wait_for_timeout(500)

    def click_continue(self):
        """Нажать кнопку Отправить."""
        self.page.locator("button:has-text('Отправить')").first.click()
        self.page.wait_for_timeout(1000)

    def go_to_lk(self):
        """Перейти в Личный кабинет обучающегося."""
        self.page.locator("div.v-list-item-title:has-text('Личный кабинет обучающегося')").first.click(force=True)
        self.page.wait_for_timeout(1000)

