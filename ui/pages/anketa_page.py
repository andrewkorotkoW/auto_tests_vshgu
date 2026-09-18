from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from utils.logger import logger


class AnketaPage(BasePage):
    """Внешняя анкета LPD, открывающаяся в новой вкладке после запуска активности."""

    def __init__(self, page: Page):
        super().__init__(page)

    def go(self):
        """Нажать «Перейти» на промежуточном экране запуска анкеты."""
        self.click_and_wait(self.page.locator("a.btn.btn-primary:has-text('Перейти')").first, force=True)

    def fill_anonymous(self):
        """Короткая анонимная анкета (2 radio) — заполнить и отправить."""
        self.wait_visible("input[name='field_1275'][value='1']")
        self.page.locator("input[name='field_1275'][value='1']").check(force=True)
        self.wait_visible("input[name='field_1276'][value='2']").check(force=True)
        self.click_and_wait("input[name='finish']", force=True)
        self._confirm_and_verify()

    def fill_authorized(self, save_only: bool = False):
        """Длинная авторизованная анкета.

        save_only=True заполняет только первые 6 полей и жмёт «Сохранить страницу»,
        не отправляя анкету целиком (сценарий «сохранить и продолжить позже»).
        """
        self.wait_visible("select[name='field_1152']")
        self.page.locator("select[name='field_1152']").select_option("2", force=True)
        self.page.locator("select[name='field_1173']").select_option("1", force=True)
        self.page.locator("input[name='field_1176[]'][value='2']").check(force=True)
        self.page.locator("input[name='field_1176[]'][value='3']").check(force=True)
        self.page.locator("input[name='field_1177'][value='2']").check(force=True)
        self.page.locator("input[name='field_1180'][value='10']").check(force=True)
        self.page.locator("input[name='field_1179']").fill("2" if save_only else "5")

        if save_only:
            save_btn = self.page.locator(
                "input[name='save'][value='Сохранить страницу'], input[value='Сохранить страницу']"
            )
            if save_btn.count() > 0 and save_btn.first.is_visible(timeout=5000):
                save_btn.first.click(force=True)
            return
        self._advance_and_finish_authorized()

    def continue_authorized(self):
        """Продолжить заполнение авторизованной анкеты со второй страницы после
        повторного открытия LPD (сценарий «сохранить и продолжить позже»)."""
        self._advance_and_finish_authorized()

    def _advance_and_finish_authorized(self):
        next_btn = self.page.locator("input[name='next']")
        if next_btn.count() > 0 and next_btn.is_visible(timeout=3000):
            next_btn.click(force=True)

        self.page.locator("input[name='field_1174']").fill("Да")
        self.page.locator("input[name='field_1175']").fill("1990-01-01")
        self.page.locator("select[name='field_1178']").select_option("4", force=True)
        self._fill_autocomplete()

        self.click_and_wait("input[value='Сохранить и Проверить ответы']", force=True)
        self._confirm_and_verify()

    def _fill_autocomplete(self):
        field = self.page.locator("input[name='field_1250']")
        if field.count() == 0:
            return
        field.click(force=True)
        self.page.evaluate(
            """
            (input) => {
                input.focus();
                input.value = '';
                const chars = 'мос';
                for (const char of chars) {
                    input.value += char;
                    input.dispatchEvent(new KeyboardEvent('keydown', {key: char}));
                    input.dispatchEvent(new KeyboardEvent('keypress', {key: char}));
                    input.dispatchEvent(new KeyboardEvent('keyup', {key: char}));
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                }
            }
            """,
            field.element_handle(),
        )
        option = self.page.locator("li[data-value='7700000000000']")
        self.wait_visible(option, timeout=15000)
        option.click(force=True)

    def _confirm_and_verify(self):
        confirm_btn = self.page.locator("input[value='Данные корректны, ответы подтверждаю']")
        self.wait_visible(confirm_btn, timeout=15000)
        try:
            self.page.evaluate(
                "document.querySelector('input[value=\"Данные корректны, ответы подтверждаю\"]').click()"
            )
        except Exception:
            confirm_btn.click(force=True)
        success = self.page.locator("div.alert-primary:has-text('Анкета успешно отправлена')")
        self.wait_visible(success, timeout=5000)
        logger.info("Анкета успешно пройдена")
