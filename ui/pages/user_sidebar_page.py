"""Боковое меню пользователя (после входа) и всплывающие окна, которые мешают кликам."""
from playwright.sync_api import Page, Locator
from ui.pages.base_page import BasePage
from utils.logger import logger

# Кнопки бокового меню обычного пользователя: подпись -> href.
SIDEBAR_BUTTONS = {
    "Мое обучение": "/education",
    "База знаний": "/library",
    "Уведомления": "/portal-notifications",
    "Техподдержка": "/support",
}
# Внешние кнопки, которые есть не у всех пользователей (зависят от организации): подпись -> подстрока href
OPTIONAL_EXTERNAL_BUTTONS = {
    "МИФ": "miflib.ru",
}


class UserSidebarPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def sidebar(self) -> Locator:
        return self.page.locator("nav, aside, .v-navigation-drawer").first

    def button(self, label: str) -> Locator:
        return self.sidebar.locator(f"a:has-text('{label}')").first

    def user_name(self) -> str:
        """ФИО пользователя в шапке (кнопка меню профиля, блок .user-menu; тега <header> на портале нет)."""
        return self.page.locator(".user-menu").first.inner_text().strip()

    def open(self, path: str) -> None:
        """Открыть раздел по URL и закрыть всё, что перекрывает страницу (онбординг есть на каждой)."""
        self.page.goto(f"{self.page.url.split('/', 3)[0]}//{self.page.url.split('/', 3)[2]}{path}")
        self.wait_loaded()
        self.dismiss_popups()

    def dismiss_popups(self) -> None:
        """Закрыть то, что перекрывает страницу после входа: анкета «заполните данные о себе»
        (чекбокс согласия + «Отправить»), cookie-баннер («Принимаю»), онбординг.
        Всё опционально: чего нет — пропускаем."""
        page = self.page
        try:
            form = page.locator(".v-overlay--active:has-text('данные о себе'), .v-dialog:has-text('данные о себе')").first
            if form.is_visible(timeout=2000):
                for cb in form.locator("input[type=checkbox]").all():
                    if not cb.is_checked():
                        cb.check(force=True)
                form.locator("button:has-text('Отправить')").first.click(force=True)
                self.wait_hidden(form, timeout=10000)
                logger.info("Анкета «данные о себе» отправлена")
        except Exception as exc:  # noqa: BLE001
            logger.info(f"Анкета не закрылась/не появилась: {exc}")
        try:
            accept = page.locator("button:has-text('Принимаю')").first
            if accept.is_visible(timeout=1500):
                accept.click(force=True)
                logger.info("Cookie-баннер принят")
        except Exception:  # noqa: BLE001
            pass
        self.pass_onboarding()

    def pass_onboarding(self, timeout_s: float = 90.0) -> None:
        """Интерактивное руководство показывается на каждой странице: «Пройти обучение»,
        затем «Далее» × N и «Завершить» (все шаги — одна кнопка data-qa=onboarding-popup-next).

        Между шагами кнопка на доли секунды исчезает, а затемнение остаётся и перехватывает
        клики, поэтому тур считаем пройденным только когда исчезло само затемнение
        (.v-overlay--active без текста), а не когда просто не видна кнопка."""
        import time
        page = self.page
        deadline = time.monotonic() + timeout_s
        try:
            start = page.locator("button:has-text('Пройти обучение')").first
            if start.is_visible(timeout=2000):
                start.click(force=True)
                logger.info("Онбординг: «Пройти обучение»")
            nxt = page.locator("[data-qa='onboarding-popup-next']").first
            while time.monotonic() < deadline:
                try:
                    nxt.wait_for(state="visible", timeout=4000)
                    label = (nxt.inner_text() or "").strip()
                    nxt.click(force=True)
                    if label.startswith("Заверш"):
                        break
                    continue
                except Exception:  # noqa: BLE001 — кнопки нет: тур либо закончился, либо между шагами
                    pass
                if not self._onboarding_dim_present():
                    break
            self.wait_hidden(page.locator(".v-overlay--active:has-text('Интерактивное руководство')").first, timeout=5000)
            if self._onboarding_dim_present():
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as exc:  # noqa: BLE001
            logger.info(f"Онбординг не появился или уже пройден: {exc}")

    def _onboarding_dim_present(self) -> bool:
        """Есть ли затемнение тура (активный overlay без содержательного текста)."""
        for ov in self.page.locator(".v-overlay--active").all():
            try:
                if not ov.inner_text().strip():
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    def go(self, label: str) -> None:
        """Перейти по кнопке меню, дождаться загрузки и пройти онбординг нового раздела."""
        self.button(label).click(force=True)
        self.wait_loaded()
        self.dismiss_popups()

    def is_404(self) -> bool:
        return self.page.locator("text=Ошибка 404").first.is_visible(timeout=500)
