from playwright.sync_api import Page, Locator, expect

from config.settings import settings


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def open(self, url: str):
        self.page.goto(url)
        self.wait_loaded()

    def click(self, selector: str):
        self.page.click(selector)

    def fill(self, selector: str, text: str):
        self.page.fill(selector, text)

    def wait_for(self, selector: str, timeout: int = None):
        self.page.wait_for_selector(selector, timeout=timeout or settings.UI_TIMEOUT)

    def get_text(self, selector: str) -> str:
        return self.page.text_content(selector)

    def _locator(self, selector) -> Locator:
        return self.page.locator(selector) if isinstance(selector, str) else selector

    # Видимые индикаторы загрузки Vuetify/портала: крутилка, скелетоны (Vuetify и портальный
    # .vs-skeleton-table/.skeleton — так грузятся таблицы админки), элемент в состоянии «занят».
    # Сюда НЕ входят v-progress-linear (верхняя полоса остаётся видимой и после полной загрузки)
    # и tr.v-data-table__progress (висит в DOM таблицы всегда) — разведка 12–13.10.2026.
    LOADING_INDICATORS = (
        ".v-progress-circular--indeterminate:visible, .v-skeleton-loader:visible, "
        ".vs-skeleton-table:visible, .skeleton:visible, [aria-busy='true']:visible"
    )
    # Самая ранняя стадия после goto/reload: SPA ещё не смонтировано, в body только пустая
    # оболочка и безклассовые <svg><circle> (дуга-лоадер), всего ~6 элементов. У неё нет
    # классов, по которым можно ждать, поэтому признак — «в body есть что-то кроме лоадера».
    _SPA_BOOTED_JS = (
        "() => !(document.body.querySelectorAll('*').length < 20 && document.body.querySelector('svg circle'))"
    )

    def wait_loaded(self, timeout: int = None):
        """Ждёт, пока страница «угомонится» после навигации/клика: DOM собран и на экране нет
        индикаторов загрузки (LOADING_INDICATORS).

        Раньше здесь был networkidle, но он (а) зависит от сторонних маячков и поллинга
        уведомлений и на медленном стенде не наступает вовсе, (б) возвращается мгновенно, пока
        на экране ещё крутится v-progress-circular — разведка на develop 12.10.2026 показала
        оба случая. Ждём состояние страницы, а не тишину сети."""
        timeout = timeout or settings.UI_TIMEOUT
        self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        self.page.wait_for_function(self._SPA_BOOTED_JS, timeout=timeout)
        expect(self.page.locator(self.LOADING_INDICATORS)).to_have_count(0, timeout=timeout)

    def wait_visible(self, selector, timeout: int = None) -> Locator:
        """Ждёт, пока locator (или селектор) станет видимым, и возвращает его."""
        locator = self._locator(selector)
        expect(locator).to_be_visible(timeout=timeout or settings.UI_TIMEOUT)
        return locator

    def wait_hidden(self, selector, timeout: int = None):
        """Ждёт, пока locator (или селектор) исчезнет/скроется."""
        expect(self._locator(selector)).to_be_hidden(timeout=timeout or settings.UI_TIMEOUT)

    def click_and_wait(self, selector, wait_for=None, timeout: int = None, force: bool = False):
        """Кликает по locator/селектору и ждёт результата вместо паузы по времени.

        wait_for может быть:
          - None — дождаться сети после клика (навигация/XHR);
          - locator/селектор — дождаться его видимости;
          - вызываемый без аргументов объект (например
            lambda: self.page.wait_for_url("**/success")) — вызывается после клика.
        """
        timeout = timeout or settings.UI_TIMEOUT
        locator = self._locator(selector)
        locator.click(force=force, timeout=timeout)
        if wait_for is None:
            self.wait_loaded(timeout=timeout)
        elif callable(wait_for):
            wait_for()
        else:
            self.wait_visible(wait_for, timeout=timeout)