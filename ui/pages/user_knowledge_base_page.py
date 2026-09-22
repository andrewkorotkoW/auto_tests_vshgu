"""Пользовательская страница «База знаний» (/library): поиск и открытие материала."""
from playwright.sync_api import Page, expect

from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class UserKnowledgeBasePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = UserSidebarPage(page)

    def open(self) -> None:
        self.sidebar.open("/library")

    def open_catalog(self) -> None:
        catalog_btn = self.page.locator("button.v-btn:has(span:has-text('Каталог'))").first
        if catalog_btn.count() == 0:
            catalog_btn = self.page.locator("button:has-text('Каталог')").first
        expect(catalog_btn).to_be_visible(timeout=15000)
        catalog_btn.click(timeout=5000)
        self.wait_loaded()

    def material_card(self, name: str):
        card = self.page.locator(f"span.library-card__name:has-text('{name}')").first
        if card.count() == 0:
            card = self.page.get_by_text(name, exact=True).first
        return card

    def open_material(self, name: str) -> None:
        card = self.material_card(name)
        expect(card).to_be_visible(timeout=15000)
        card.click(timeout=5000)
        self.wait_loaded()

    def expect_material_title_visible(self, name: str) -> None:
        title = self.page.locator(f"h2.material-header__title:has-text('{name}')")
        expect(title).to_be_visible(timeout=15000)
