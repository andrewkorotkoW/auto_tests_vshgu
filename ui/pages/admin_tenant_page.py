"""Карточка тенанта в админке — блок интеграции с МТС Линк (часть 0.1).

Разведка на --env develop (только чтение, через код существующих тестов/page objects —
живого браузера в этой среде нет) подтвердила путь карточки тенанта и набор вкладок:
`/admin/organization/{id}` с вкладками «Управление» (пользователи), «Настройки»
(брендинг), «Связь ОМТ КАС» (оргструктура) — см. docstring `api/endpoints/mts_link.py`.
Блока интеграции МТС Линк там сейчас нет ни на одной вкладке — функциональности ещё
нет ни на одной ветке. Селекторы ниже — по аналогии со стилем существующих вкладок
карточки тенанта (`a.v-tab`/`div.v-list-item-title`, см. `ui/pages/admin_page.py`,
`ui/pages/admin_programs_page.py`) и текстовым меткам из требований части 0.1
(`docs/requirements/tz2026/mts_link/11_часть_0.1_настройка_интеграции_в_карточке_тенанта.md`).
TODO: уточнить после появления ветки — каждый локатор.
"""
from playwright.sync_api import Page, expect
from ui.pages.base_page import BasePage
from config.settings import settings


class AdminTenantPage(BasePage):
    PATH = "/admin/organization"

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self, ui_base_url: str, tenant_id: int) -> None:
        self.page.goto(f"{ui_base_url}{self.PATH}/{tenant_id}")
        self.wait_loaded()

    def open_integrations_tab(self) -> None:
        """Вкладка с настройками интеграций тенанта. TODO: уточнить после ветки —
        сейчас в карточке тенанта такой вкладки нет вовсе (см. модуль docstring)."""
        tab = self.page.locator("a.v-tab", has_text="Интеграции")
        expect(tab).to_be_visible(timeout=settings.UI_TIMEOUT)
        tab.click(timeout=settings.UI_TIMEOUT)

    # ── блок МТС Линк ────────────────────────────────────────────────────

    def token_field(self):
        return self.page.locator("[data-qa='mts-link-token-input']")

    def fill_token(self, token: str) -> None:
        field = self.token_field()
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(token, timeout=settings.UI_TIMEOUT)

    def save_button(self):
        return self.page.locator("[data-qa='mts-link-save-button']")

    def save(self) -> None:
        button = self.save_button()
        expect(button).to_be_enabled(timeout=settings.UI_TIMEOUT)
        button.click(timeout=settings.UI_TIMEOUT)

    def masked_token_text(self) -> str:
        """Текст замаскированного токена (часть 0.1, раздел «Отображение токена») —
        первые символы + звёздочки, без полного значения."""
        locator = self.page.locator("[data-qa='mts-link-token-masked']")
        expect(locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        return locator.text_content() or ""

    def error_message(self) -> str:
        locator = self.page.locator("[data-qa='mts-link-settings-error']")
        expect(locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        return locator.text_content() or ""

    def integration_configured_badge_visible(self) -> bool:
        """Признак «интеграция настроена и проверена» в карточке тенанта."""
        return self.page.locator("[data-qa='mts-link-integration-configured']").is_visible(timeout=5000)
