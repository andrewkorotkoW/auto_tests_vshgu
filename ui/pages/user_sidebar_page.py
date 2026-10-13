"""Боковое меню пользователя (после входа) и всплывающие окна, которые мешают кликам."""
import time

from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError, expect
from ui.pages.base_page import BasePage
from utils.logger import logger

# Всё, что может перекрыть страницу после входа/навигации, одним списком — dismiss_popups
# ждёт появления *любого* из них один раз, а не каждого по очереди со своим таймаутом.
ANKETA_SELECTOR = ".v-overlay--active:has-text('данные о себе'), .v-dialog:has-text('данные о себе')"
MAILING_NOTICE_SELECTOR = "div.v-dialog:has-text('Вы отказались от получения информационных писем')"
COOKIE_ACCEPT_SELECTOR = "button:has-text('Принимаю')"
TOUR_START_SELECTOR = "button:has-text('Пройти обучение')"
TOUR_NEXT_SELECTOR = "[data-qa='onboarding-popup-next']"
BLOCKER_SELECTORS = (
    ANKETA_SELECTOR, MAILING_NOTICE_SELECTOR, COOKIE_ACCEPT_SELECTOR, TOUR_START_SELECTOR, TOUR_NEXT_SELECTOR,
)
ANY_BLOCKER_SELECTOR = ", ".join(f"{s}:visible" for sel in BLOCKER_SELECTORS for s in sel.split(", "))
# Попап после загрузки страницы появляется в пределах секунды после ответа GET /onboarding
# (/me/agreements для анкеты), а оба запроса SPA делает при старте — к концу wait_loaded()
# они уже отработали. 4 с — запас на анимацию диалога и медленный стенд.
POPUP_GRACE_MS = 4000
# Следующий попап (например, тур после анкеты) приходит сразу за предыдущим.
NEXT_POPUP_GRACE_MS = 2500

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

    def remove_tech_banner(self) -> None:
        """Убрать оранжевую плашку «Технические работы»: она прижимает шапку и закрывает
        меню пользователя. Убираем из DOM, чтобы не зависеть от её кнопки. Тесты самого
        баннера этот метод не зовут (они проверяют плашку)."""
        try:
            if self.page.locator("div.tech-banner").count():
                self.page.evaluate("() => document.querySelectorAll('div.tech-banner').forEach(el => el.remove())")
                logger.info("Плашка «Технические работы» убрана")
        except Exception:  # noqa: BLE001
            pass

    def dismiss_anketa(self) -> None:
        """Закрыть анкету «заполните данные о себе» (чекбокс согласия + «Отправить»),
        которая блокирует страницу сразу после первого входа. Опционально: если анкеты
        нет (уже заполнена ранее), молча пропускаем."""
        page = self.page
        try:
            form = page.locator(".v-overlay--active:has-text('данные о себе'), .v-dialog:has-text('данные о себе')").first
            form.wait_for(state="visible", timeout=5000)
            for cb in form.locator("input[type=checkbox]").all():
                if cb.is_checked():
                    continue
                # Сам <input> скрыт (opacity 0), а check(force=True) по нему пропускает
                # проверку стабильности: клик во время enter-анимации диалога не меняет
                # состояние (12.10.2026, когда login перестал ждать networkidle). Кликаем
                # по видимой обёртке контрола обычным кликом и проверяем результат —
                # то же, что LoginPage.handle_modal.
                control = cb.locator("xpath=ancestor::*[contains(@class,'v-selection-control')][1]")
                if control.count():
                    control.first.click(timeout=5000)
                else:
                    cb.check(force=True)
                expect(cb).to_be_checked(timeout=5000)
            form.locator("button:has-text('Отправить')").first.click(force=True)
            self.wait_hidden(form, timeout=10000)
            logger.info("Анкета «данные о себе» отправлена")
        except Exception as exc:  # noqa: BLE001
            logger.info(f"Анкета не закрылась/не появилась: {exc}")

    def dismiss_popups(self, grace_ms: int = POPUP_GRACE_MS) -> None:
        """Закрыть то, что перекрывает страницу после входа: анкета «заполните данные о себе»
        (чекбокс согласия + «Отправить»), уведомление об отказе от рассылки,
        cookie-баннер («Принимаю»), онбординг. Всё опционально: чего нет — пропускаем.

        Ждём появления *любого* блокера один раз (grace_ms), закрываем найденный и смотрим
        снова — следующий попап может прийти сразу за предыдущим (тур после анкеты). Раньше
        каждый блокер ждали по очереди своим таймаутом (5 + 5 + 3 + 12 + 4 с), и у подготовленного
        через API пользователя, у которого ничего не показывается, вызов стоил ~30 с —
        при трёх вызовах в open_individual_tab это 88 из 140 с теста (allure run 65, 13.10.2026)."""
        page = self.page
        self.remove_tech_banner()
        # Тесты зовут dismiss_popups сразу после goto: попапы приходят после ответов API, которые
        # SPA делает при старте — дожидаемся сборки страницы (дёшево, если она уже собрана),
        # иначе grace истечёт раньше, чем тур на тяжёлой странице (поток в админке) появится.
        try:
            self.wait_loaded()
        except Exception as exc:  # noqa: BLE001 — страница не «угомонилась»: попапы всё равно проверим
            logger.info(f"dismiss_popups: wait_loaded не дождался: {str(exc)[:120]}")
        deadline = time.monotonic() + 120
        wait_ms = grace_ms
        handled: list = []
        while time.monotonic() < deadline:
            try:
                page.locator(ANY_BLOCKER_SELECTOR).first.wait_for(state="visible", timeout=wait_ms)
            except PlaywrightTimeoutError:
                break
            kind = self._dismiss_one_blocker()
            if not kind:
                break
            if handled.count(kind) >= 2:
                # Один и тот же попап не закрывается второй раз подряд — дальше крутиться нет смысла,
                # пусть упадёт следующий шаг теста с понятным сообщением, а не этот цикл по дедлайну.
                logger.warning(f"dismiss_popups: «{kind}» остаётся на экране после закрытия — прекращаем")
                break
            handled.append(kind)
            wait_ms = NEXT_POPUP_GRACE_MS
        if self._onboarding_dim_present():
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

    def _dismiss_one_blocker(self) -> str:
        """Закрыть первый из видимых блокеров, вернуть его вид. '' — ничего видимого не нашли.

        Порядок важен: тур держит затемнение поверх всей страницы, и клик по cookie-баннеру
        под ним уходит в затемнение (force=True не спасает — событие получает scrim)."""
        page = self.page
        if page.locator(ANKETA_SELECTOR).first.is_visible():
            self.dismiss_anketa()
            return "anketa"
        notice = page.locator(MAILING_NOTICE_SELECTOR).first
        if notice.is_visible():
            try:
                notice.locator("button:has-text('Понятно')").first.click(timeout=5000)
                self.wait_hidden(notice, timeout=10000)
                logger.info("Уведомление об отказе от рассылки закрыто")
            except Exception as exc:  # noqa: BLE001
                logger.info(f"Уведомление об отказе от рассылки не закрылось: {str(exc)[:120]}")
            return "mailing_notice"
        if page.locator(TOUR_START_SELECTOR).first.is_visible() or page.locator(TOUR_NEXT_SELECTOR).first.is_visible():
            self.pass_onboarding()
            return "tour"
        accept = page.locator(COOKIE_ACCEPT_SELECTOR).first
        if accept.is_visible():
            try:
                # обычный клик: дождётся, пока кнопку ничто не перекрывает (затемнение тура ушло)
                accept.click(timeout=5000)
            except PlaywrightTimeoutError:
                accept.dispatch_event("click")
            try:
                self.wait_hidden(accept, timeout=5000)
                logger.info("Cookie-баннер принят")
            except AssertionError:
                logger.info("Cookie-баннер не скрылся после «Принимаю»")
            return "cookie"
        return ""

    def pass_onboarding(self, timeout_s: float = 90.0, grace_ms: int = POPUP_GRACE_MS) -> None:
        """Интерактивное руководство показывается на каждой странице: «Пройти обучение»,
        затем «Далее» × N и «Завершить» (все шаги — одна кнопка data-qa=onboarding-popup-next).

        Между шагами кнопка на доли секунды исчезает, а затемнение остаётся и перехватывает
        клики, поэтому тур считаем пройденным только когда исчезло само затемнение
        (.v-overlay--active без текста), а не когда просто не видна кнопка.

        Если за grace_ms не появилось ни вводное окно, ни кнопка шага — тура нет (истории
        закрыты через API, см. prepared_user), выходим сразу, а не через 12 + 4 с."""
        page = self.page
        deadline = time.monotonic() + timeout_s
        try:
            start = page.locator(TOUR_START_SELECTOR).first
            nxt = page.locator(TOUR_NEXT_SELECTOR).first
            try:
                page.locator(f"{TOUR_START_SELECTOR}:visible, {TOUR_NEXT_SELECTOR}:visible").first.wait_for(
                    state="visible", timeout=grace_ms
                )
            except PlaywrightTimeoutError:
                if self._onboarding_dim_present():
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                return
            if start.is_visible():
                # клик по ещё анимирующемуся окну теряется — нажимаем, проверяем, что окно ушло, иначе повторяем
                for attempt in range(3):
                    start.click()
                    try:
                        start.wait_for(state="hidden", timeout=3000)
                        break
                    except Exception:  # noqa: BLE001
                        logger.info(f"Онбординг: «Пройти обучение» не сработало, попытка {attempt + 1}")
                logger.info("Онбординг: «Пройти обучение»")
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

    # ---- «Индивидуальное обучение»: контент, назначенный слушателю напрямую ----
    def open_individual_tab(self, tab_name: str) -> None:
        """Открыть вкладку раздела «Индивидуальное обучение» (Курсы и тесты / ЛПД /
        Мои материалы / Игровая сессия / Расписание).

        Путь: /education -> клик по баннеру «Индивидуальное обучение»
        (a.individual-education-banner__link) -> /education/personal/schedule, где
        отдельно от общего онбординга стартует тур раздела («1 из 8», кнопка
        data-qa=onboarding-popup-next) -> клик по вкладке. Без прохождения этого
        тура затемнение перехватывает клик по вкладке."""
        self.open("/education")
        banner = self.page.locator("text=Индивидуальное обучение").first
        expect(banner).to_be_visible(timeout=15000)
        banner.click(force=True)
        self.wait_loaded()
        self.dismiss_popups()

        tab = self.page.locator(f"xpath=//span[normalize-space()='{tab_name}']").first
        expect(tab).to_be_visible(timeout=15000)
        tab.click(force=True)
        self.wait_loaded()
        self.dismiss_popups()
