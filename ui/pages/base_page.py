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

    def _select_first_dropdown_item(self, select_locator: Locator) -> None:
        """Открывает Vuetify v-select/v-autocomplete и выбирает первый реальный пункт
        списка. Перенесено из ui/pages/admin_programs_page.py (было приватным методом
        AdminProgramsPage, используется и для полей карточки «Создать Активити»
        в ui/pages/admin_event_mts_page.py) — логика не завязана на конкретную форму."""
        expect(select_locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        # Без force=True: клик должен реально попасть в комбобокс, иначе дропдаун для
        # другого поля молча остаётся незаполненным.
        select_locator.click(timeout=settings.UI_TIMEOUT)
        # Дропдаун ищем по id из aria-owns этого конкретного комбобокса, а не первый
        # попавшийся "активный" v-menu на странице — после модалок их v-menu иногда
        # остаётся в DOM с классом ...active, и общий локатор стабильно попадал туда.
        list_id = select_locator.get_attribute("aria-owns")
        if list_id:
            dropdown_items = self.page.locator(f"#{list_id} >> xpath=.//div[contains(@class,'v-list-item__content')]")
        else:
            dropdown_items = self.page.locator(
                "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
                "//div[contains(@class,'v-list-item__content')]"
            )
        expect(dropdown_items.first).to_be_visible(timeout=settings.UI_TIMEOUT)
        # Список опций у части селектов подгружается асинхронно после открытия: первым
        # в DOM оказывается плейсхолдер «Загрузка списка», который не является реальным
        # пунктом и клик по нему не устанавливает v-model. Ждём реальный пункт.
        expect(dropdown_items.first).not_to_have_text("Загрузка списка", timeout=settings.UI_TIMEOUT)
        dropdown_items.first.click(timeout=5000)

    def _select_by_label(self, label_text: str) -> None:
        self._select_first_dropdown_item(
            self.page.locator(
                f"xpath=//label[contains(normalize-space(),'{label_text}')]"
                "/ancestor::div[contains(@class,'v-input')][1]"
            )
        )

    def _select_item_containing_by_label(self, label_text: str, contains_text: str) -> None:
        """Как _select_by_label, но выбирает пункт, СОДЕРЖАЩИЙ contains_text (а не
        первый попавшийся) — для мультиселектов с готовым набором пунктов (без
        дозаполнения текста в поле, в отличие от _select_exact_value_by_label),
        например «Преподаватели» в ui/pages/admin_event_mts_page.py, где нужен
        конкретный человек по фрагменту email в подписи пункта."""
        select_locator = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{label_text}')]"
            "/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        select_locator.click(timeout=settings.UI_TIMEOUT)

        list_id = select_locator.get_attribute("aria-owns")
        if list_id:
            option = self.page.locator(
                f"#{list_id} >> xpath=.//div[contains(@class,'v-list-item__content')][contains(.,'{contains_text}')]"
            )
        else:
            option = self.page.locator(
                "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
                f"//div[contains(@class,'v-list-item__content') and contains(.,'{contains_text}')]"
            )
        expect(option.first).to_be_visible(timeout=settings.UI_TIMEOUT)
        option.first.click(timeout=5000)

    def _select_exact_value_by_label(self, label_text: str, value: str) -> None:
        """Как _select_by_label, но допечатывает текст в поле и выбирает пункт с
        точным совпадением (для селектов, которые фильтруют список по вводу, а не
        просто показывают готовый набор — см. select_program_type_value в
        admin_programs_page.py)."""
        select_locator = self.page.locator(
            f"xpath=//label[contains(normalize-space(),'{label_text}')]"
            "/ancestor::div[contains(@class,'v-input')][1]"
        )
        expect(select_locator).to_be_visible(timeout=settings.UI_TIMEOUT)
        select_locator.click(timeout=settings.UI_TIMEOUT)
        select_locator.locator("input").first.fill(value, timeout=5000)

        list_id = select_locator.get_attribute("aria-owns")
        if list_id:
            option = self.page.locator(
                f"#{list_id} >> xpath=.//div[contains(@class,'v-list-item__content')][normalize-space()='{value}']"
            )
        else:
            option = self.page.locator(
                "xpath=//div[contains(@class,'v-menu__content') and contains(@class,'menuable__content__active')]"
                f"//div[contains(@class,'v-list-item__content') and normalize-space()='{value}']"
            )
        expect(option.first).to_be_visible(timeout=settings.UI_TIMEOUT)
        option.first.click(timeout=5000)

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