"""Админка → База пользователей (/admin/users): поиск, строка пользователя, чипы колонки «Синхронизация»."""
from typing import Optional

from playwright.sync_api import Page, Locator
from ui.pages.base_page import BasePage
from utils.logger import logger

SYNC_COLUMN_INDEX = 8  # 0 — чекбокс, 1 — ID, 2 — почта, 3 — ФИО, 4 — дата, 5 — Альпина, 6 — МИФ, 7 — тип регистрации, 8 — Синхронизация
BUK_SYNCED_TOOLTIP = "Синхронизирован"


class AdminUsersPage(BasePage):
    PATH = "/admin/users"

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str) -> None:
        self.page.goto(f"{ui_base_url}{self.PATH}")
        self.wait_loaded()
        self.page.locator('[data-qa="km-search"]').first.wait_for(state="visible", timeout=30000)

    def search(self, query: str) -> None:
        """Поиск в шапке таблицы. Режим по умолчанию — «ФИО», поэтому ищем по фамилии и имени, не по email."""
        box = self.page.locator('[data-qa="km-search"]').first
        box.fill("")
        box.fill(query)
        self.page.keyboard.press("Enter")
        self.wait_loaded()
        self.page.wait_for_timeout(1500)

    def row_for(self, user: dict) -> Locator:
        """Строка таблицы для пользователя (ищем по ФИО, затем сверяем email в строке)."""
        self.search(f"{user['surname']} {user['name']}")
        row = self.page.locator(f"tr:has-text('{user['email']}')").first
        row.wait_for(state="visible", timeout=15000)
        return row

    def sync_chips(self, row: Locator) -> Locator:
        return row.locator("td").nth(SYNC_COLUMN_INDEX).locator(".sync-chip")

    def sync_chip(self, row: Locator, label: str) -> Locator:
        """Чип колонки «Синхронизация» по подписи: «КАС» или «БУК»."""
        return self.sync_chips(row).filter(has_text=label).first

    def chip_icon_color(self, chip: Locator) -> str:
        return chip.locator(".v-icon").first.evaluate("e => getComputedStyle(e).color")

    def tooltip_of(self, chip: Locator) -> Optional[str]:
        """Навести курсор на чип и вернуть текст всплывающей подсказки (v-tooltip)."""
        self.page.mouse.move(0, 0)
        self.page.wait_for_timeout(200)
        chip.hover()
        tip = self.page.locator(".v-tooltip__content.menuable__content__active, .v-tooltip__content:visible").first
        try:
            tip.wait_for(state="visible", timeout=5000)
            text = tip.inner_text().strip()
        except Exception:  # noqa: BLE001
            text = None
        logger.info(f"Подсказка чипа «{chip.inner_text().strip()}»: {text!r}")
        return text
