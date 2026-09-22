"""Пользовательская страница «База знаний» (/library): поиск и открытие материала."""
from urllib.parse import unquote

from playwright.sync_api import Page, expect

from ui.pages.base_page import BasePage
from ui.pages.user_sidebar_page import UserSidebarPage


class UserKnowledgeBasePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = UserSidebarPage(page)

    def open(self, ui_base_url: str) -> None:
        # UserSidebarPage.open() строит URL относительно текущего page.url — не подходит
        # для свежей страницы (about:blank), поэтому здесь переходим напрямую.
        self.page.goto(f"{ui_base_url.rstrip('/')}/library")
        self.wait_loaded()
        self.sidebar.dismiss_popups()

    def open_catalog(self) -> None:
        catalog_btn = self.page.locator("button.v-btn:has(span:has-text('Каталог'))").first
        if catalog_btn.count() == 0:
            catalog_btn = self.page.locator("button:has-text('Каталог')").first
        expect(catalog_btn).to_be_visible(timeout=15000)
        catalog_btn.click(timeout=5000)
        self.wait_loaded()

    def search(self, query: str) -> None:
        """Заполнить поле поиска и нажать Enter.

        На каталоге с большим числом материалов взаимодействие с поиском нестабильно:
        fill() иногда не долетает до модели (после Enter filter="" в URL), а иногда
        срабатывает какой-то отложенный watcher и перетирает уже применённый фильтр
        обратно на пустой. Печатаем посимвольно и повторяем весь цикл ввод+Enter,
        пока URL действительно не отразит наш запрос."""
        field = self.page.get_by_placeholder("Поиск")
        expect(field).to_be_visible(timeout=15000)
        for _ in range(5):
            field.click(timeout=5000)
            field.fill("", timeout=5000)
            field.press_sequentially(query, timeout=10000)
            if field.input_value() != query:
                self.page.wait_for_timeout(500)
                continue
            self.page.keyboard.press("Enter")
            self.wait_loaded()
            self.page.wait_for_timeout(1000)
            if query in unquote(self.page.url):
                return
        raise AssertionError(f"Поиск не применил фильтр '{query}': url={self.page.url}")

    def material_card(self, name: str):
        card = self.page.locator(f"span.library-card__name:has-text('{name}')").first
        if card.count() == 0:
            card = self.page.get_by_text(name, exact=True).first
        return card

    def open_material(self, name: str) -> None:
        self.search(name)
        card = self.material_card(name)
        expect(card).to_be_visible(timeout=15000)
        card.click(timeout=5000)
        self.wait_loaded()

    def expect_material_title_visible(self, name: str) -> None:
        title = self.page.locator(f"h2.material-header__title:has-text('{name}')")
        expect(title).to_be_visible(timeout=15000)
