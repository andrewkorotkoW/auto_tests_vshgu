"""Карточка тенанта в админке — вкладка интеграции с МТС Линк.

Подтверждено живой разведкой на стенде mts-link-release-main 29.10.2026:
`/admin/organization/{id}` — вкладки «Управление», «Настройки», «Связь ОМТ КАС»,
«МТС Линк» (4-я, `?tab=3` в query, но открывать лучше кликом по вкладке — порядковый
номер в query не гарантирован стабильным). На develop/других ветках блока интеграции
может не быть (см. is_feature_ready("MTS_LINK_READY") в tests/ui/mts_link/conftest.py)
— этот файл разведан только на mts-link-release-main.

Вкладка: переключатель «Интеграция МТС Линк» (включена/выключена), статус
«Интеграция проверена» и поле «Токен» (замаскировано плейсхолдером вида `***c4de7`,
реальное значение никогда не приходит в DOM) с кнопкой «Сохранить». Токен — рабочий,
единственный на организацию (см. docs/test_cases/mts_link/16_prod_safe_run.md, раздел
«Правила безопасного тестирования») — автотесты должны только читать это состояние,
не менять и не сохранять валидный токен.
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
        # Карточка тенанта грузит содержимое вкладок отдельным запросом ПОСЛЕ того, как
        # wait_loaded() уже не видит общих индикаторов загрузки — на медленном стенде
        # это видимый разрыв (голый спиннер без .v-progress-circular--indeterminate
        # поверх уже отрисованного сайдбара), подтверждено разведкой 29.10.2026. Ждём
        # появления самих вкладок явно, а не полагаемся на один общий wait_loaded().
        expect(self.page.locator("xpath=//div[contains(@class,'v-tab')]").first).to_be_visible(
            timeout=settings.UI_TIMEOUT * 3
        )

    def mts_link_tab(self):
        return self.page.locator("xpath=//div[contains(@class,'v-tab') and normalize-space()='МТС Линк']")

    def is_mts_link_tab_visible(self) -> bool:
        """Вкладка видна только тем, у кого есть право на неё — проверка для роли admin.
        is_visible() сам по себе не повторяет попытку (в отличие от expect(...).
        to_be_visible()), поэтому ждём явно и гасим таймаут в False."""
        try:
            expect(self.mts_link_tab()).to_be_visible(timeout=settings.UI_TIMEOUT)
            return True
        except AssertionError:
            return False

    def open_mts_link_tab(self) -> None:
        tab = self.mts_link_tab()
        expect(tab).to_be_visible(timeout=settings.UI_TIMEOUT)
        tab.click(timeout=settings.UI_TIMEOUT)
        expect(self.integration_toggle()).to_be_visible(timeout=settings.UI_TIMEOUT)

    # ── блок МТС Линк ────────────────────────────────────────────────────

    def integration_toggle(self):
        """Переключатель «Интеграция МТС Линк» (включена/выключена)."""
        return self.page.locator(
            "xpath=//label[normalize-space()='Интеграция МТС Линк']/preceding::input[@role='switch'][1]"
        )

    def is_integration_enabled(self) -> bool:
        toggle = self.integration_toggle()
        expect(toggle).to_be_visible(timeout=settings.UI_TIMEOUT)
        return toggle.get_attribute("aria-checked") == "true"

    def token_field(self):
        return self.page.locator("xpath=//label[normalize-space()='Токен']/following::input[1]")

    def fill_token(self, token: str) -> None:
        field = self.token_field()
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        field.fill(token, timeout=settings.UI_TIMEOUT)

    def save_button(self):
        return self.page.locator("xpath=//button[.//span[normalize-space()='Сохранить']]")

    def save(self) -> None:
        button = self.save_button()
        expect(button).to_be_enabled(timeout=settings.UI_TIMEOUT)
        button.click(timeout=settings.UI_TIMEOUT)

    def masked_token_placeholder(self) -> str:
        """Плейсхолдер поля токена (вид `***c4de7` — последние символы реального
        токена организации) — само поле всегда пустое, полное значение в DOM не
        приходит."""
        field = self.token_field()
        expect(field).to_be_visible(timeout=settings.UI_TIMEOUT)
        return field.get_attribute("placeholder") or ""

    def integration_status_text(self) -> str:
        """Текст статуса интеграции — например, «Интеграция проверена». Блок несёт
        BEM-класс organization-mts-link__status (модификатор _verified при успешной
        проверке) — единственное место в этой вкладке с осмысленным классом, не
        угаданным по аналогии."""
        locator = self.page.locator(".organization-mts-link__status")
        expect(locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        return locator.text_content() or ""

    def is_integration_verified(self) -> bool:
        return "проверена" in self.integration_status_text().lower()
