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
# Пункт меню пользователя (выпадающий список под ФИО в шапке) для синхронизированных с БУК
BUK_MENU_LABEL = "БУК «Перспектива»"
BUK_LINK_PART = "goto-lpd/buk"


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

    def dismiss_anketa(self) -> None:
        """Закрыть анкету «заполните данные о себе» (чекбокс согласия + «Отправить»),
        которая блокирует страницу сразу после первого входа. Опционально: если анкеты
        нет (уже заполнена ранее), молча пропускаем."""
        page = self.page
        # Оранжевая плашка «Технические работы» прижимает шапку и закрывает меню пользователя — убираем из DOM
        try:
            if page.locator("div.tech-banner").count():
                page.evaluate("() => document.querySelectorAll('div.tech-banner').forEach(el => el.remove())")
                logger.info("Плашка «Технические работы» убрана")
        except Exception:  # noqa: BLE001
            pass
        try:
            form = page.locator(".v-overlay--active:has-text('данные о себе'), .v-dialog:has-text('данные о себе')").first
            form.wait_for(state="visible", timeout=5000)
            for cb in form.locator("input[type=checkbox]").all():
                if not cb.is_checked():
                    cb.check(force=True)
            form.locator("button:has-text('Отправить')").first.click(force=True)
            self.wait_hidden(form, timeout=10000)
            logger.info("Анкета «данные о себе» отправлена")
        except Exception as exc:  # noqa: BLE001
            logger.info(f"Анкета не закрылась/не появилась: {exc}")

    def dismiss_popups(self) -> None:
        """Закрыть то, что перекрывает страницу после входа: анкета «заполните данные о себе»
        (чекбокс согласия + «Отправить»), cookie-баннер («Принимаю»), онбординг.
        Всё опционально: чего нет — пропускаем."""
        page = self.page
        self.dismiss_anketa()
        try:
            accept = page.locator("button:has-text('Принимаю')").first
            accept.wait_for(state="visible", timeout=3000)
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
            try:
                start.wait_for(state="visible", timeout=5000)
                start.click(force=True)
                logger.info("Онбординг: «Пройти обучение»")
            except Exception:  # noqa: BLE001 — кнопки нет: тур уже начат или не появится
                pass
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

    # ---- меню пользователя в шапке (ФИО → выпадающий список) ----
    def open_user_menu(self) -> Locator:
        """Открыть выпадающее меню под ФИО и вернуть его overlay."""
        self.close_tour_dialog()
        self.page.locator(".user-menu button").first.click()
        menu = self.page.locator(".v-overlay--active:has-text('Мой профиль')").first
        menu.wait_for(state="visible", timeout=10000)
        return menu

    def user_menu_items(self) -> list:
        """Тексты пунктов открытого меню пользователя."""
        menu = self.open_user_menu()
        return [t.strip() for t in menu.locator("a, .v-list-item").all_inner_texts() if t.strip()]

    def buk_menu_item(self) -> Locator:
        """Пункт «АИС «БУК «Перспектива»»» в открытом меню пользователя (ссылка в новую вкладку)."""
        return self.page.locator(f".v-overlay--active a:has-text('{BUK_MENU_LABEL}')").first

    def close_menu(self) -> None:
        self.page.keyboard.press("Escape")

    def close_tour_dialog(self) -> None:
        """Диалог «Интерактивное руководство» иногда остаётся с затемнением (например, на странице
        404 туру некуда идти) и перекрывает шапку. Сначала штатно: Escape и клик по затемнению;
        если не помогло — прячем overlay скриптом и пишем предупреждение, это обход, а не проверка."""
        page = self.page
        dialog = page.locator(".v-overlay--active:has-text('Интерактивное руководство')").first
        if not dialog.count() or not dialog.is_visible(timeout=500):
            return
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        try:
            page.locator(".v-overlay__scrim").first.click(position={"x": 5, "y": 5}, timeout=1000, force=True)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(300)
        if dialog.is_visible(timeout=500):
            logger.warning("Диалог онбординга не закрывается штатно — скрываем overlay скриптом (обход)")
            page.evaluate("() => document.querySelectorAll('.v-overlay--active').forEach(o => o.remove())")

    def go(self, label: str) -> None:
        """Перейти по кнопке меню, дождаться загрузки и пройти онбординг нового раздела."""
        self.button(label).click(force=True)
        self.wait_loaded()
        self.dismiss_popups()

    def is_404(self) -> bool:
        return self.page.locator("text=Ошибка 404").first.is_visible(timeout=500)
