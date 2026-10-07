import re
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect
from ui.pages.base_page import BasePage
from config.settings import settings
from utils.logger import logger


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    def login(
        self,
        email: str,
        password: str,
        base_url: str = None,
        handle_onboarding: bool = True,
        tenant_name: str = None,
    ):
        self.page.goto(f"{base_url or settings.UI_BASE_URL}/auth/main")
        self.wait_for('input[name="email_or_login"]')
        self.fill('input[name="email_or_login"]', email)
        self.fill('input[name="password"]', password)

        self.click('button:has-text("Войти")')
        self.page.wait_for_load_state("networkidle")
        self.select_tenant_if_required(base_url=base_url, tenant_name=tenant_name)
        if handle_onboarding:
            self.handle_modal()
            self.complete_training()

    def select_tenant_if_required(self, base_url: str = None, tenant_name: str = None):
        """Выбирает тенант после входа, если пользователю доступно несколько организаций.

        При единственном тенанте страница выбора не появляется, поэтому ожидание
        ограничено локальным таймаутом и не влияет на обычную авторизацию.
        """
        tenant_form = self.page.locator(".tenant-form")

        try:
            tenant_form.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            return

        links = tenant_form.get_by_role("link")
        target_domain = urlparse(base_url or settings.UI_BASE_URL).hostname

        if tenant_name:
            target_link = links.filter(has_text=tenant_name).first
        elif target_domain:
            target_link = links.filter(has_text=target_domain).first
        else:
            target_link = links.filter(
                has_text=re.compile("ВШГУ|Высшая школа государственного управления", re.I)
            ).first

        expect(target_link).to_be_visible(timeout=10000)
        target_link.click(timeout=5000)
        expect(self.page).not_to_have_url(
            re.compile(r".*/auth/tenant/select.*"),
            timeout=30000,
        )

    def handle_modal(self):
        """Обработать модальное окно после логина."""
        # В новой разметке один диалог содержит вложенные card/container с тем
        # же текстом. Берём корневой dialog, иначе Playwright получает strict mode
        # violation на трёх совпадениях.
        modal = self.page.get_by_role("dialog").filter(has_text="Отправить").first

        try:
            modal.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            logger.info("Модальное окно не появилось")
            return
        # Чекбокс согласия в Vuetify визуально скрыт (opacity 0), is_visible() даёт False —
        # поэтому отмечаем force, как в UserSidebarPage.dismiss_anketa; иначе «Отправить»
        # уходит без согласия, анкета остаётся и перекрывает страницу (07.10, после слияния).
        try:
            for checkbox in modal.locator('input[type="checkbox"]').all():
                if not checkbox.is_checked():
                    checkbox.check(force=True, timeout=5000)
            submit = modal.get_by_role("button", name="Отправить", exact=True)
            if submit.count():
                submit.first.click(force=True, timeout=5000)
            modal.wait_for(state="hidden", timeout=10000)
            logger.info("✅ Модальное окно обработано")
        except PlaywrightTimeoutError as exc:
            logger.warning(f"Модальное окно не закрылось: {str(exc)[:120]}")

    def complete_training(self):  # ← переименовано
        try:
            start_btn = self.page.locator("span.v-btn__content:has-text('Пройти обучение')")
            if start_btn.is_visible(timeout=3000):
                start_btn.click()
                logger.info("✅ Нажали 'Пройти обучение'")
            while self.page.locator("text=Далее").is_visible(timeout=2000):
                self.click("text=Далее")
            if self.page.locator("text=Завершить").first.is_visible(timeout=2000):
                self.page.locator("text=Завершить").first.click(force=True)
                self.wait_loaded()
            logger.info("✅ Обучение завершено")
        except Exception as e:
            logger.info(f"Обучение не появилось: {e}")

    def logout(self):
        """Выйти из системы."""
        # Клик по аватарке — первая v-btn в хедере, ждём появления пункта "Выйти"
        logout_icon = self.page.locator("svg[icon='logout']").first
        self.click_and_wait(self.page.locator("header .v-btn").first, wait_for=logout_icon)
        # Клик по "Выйти"
        self.click_and_wait(logout_icon)
