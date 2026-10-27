"""OpenLRS (`/lrs-admin/*`) — отдельное Laravel Backpack-приложение (тема tabler,
DataTables — тот же стек, что у хелпдеска, см. ui/pages/helpdesk_base_page.py), не связанное
с остальной Vue-админкой портала. Разведка — docs/lrs/lrs_recon.md, кейсы —
docs/test_cases/lrs.md (TC-LRS-001…015).

Штатный вход — SSO через OAuth2 (Laravel Passport): LMS-сессия → `GET <lrs>/oauth2/auth/
callback` → OpenLRS логинит того же пользователя LMS. Собственная форма `/lrs-admin/login`
учётки LMS не принимает (TC-LRS-003/015) — используется только как негативный кейс. На
develop (на момент написания) OAuth-клиент OpenLRS не зарегистрирован в Passport портала —
callback возвращает форму входа LMS/`invalid_client` (docs/plans/2026-10-14_lrs_mission.md);
`login_via_sso` это не глушит, падает таймаутом `expect`, как и должно быть видно тесту.

Разделы хранилища (`/lrs-admin/store/{id}/...`) — таблицы DataTables с server-side поиском:
как и в хелпдеске, редирект после сабмита формы/фильтра отделён от реального
`POST …/search`, поэтому любое открытие/обновление таблицы ждёт именно этот ответ
(`LrsAdminPage._is_table_search`, приём скопирован из HelpdeskAdminPage).

Фильтры Statements/States — панель Backpack `nav.navbar-filters`: каждый фильтр — `li[filter-name=…]`
с `a.dropdown-toggle`, виджет внутри закрытого dropdown (сначала открыть, потом кликать по
select2/полю). Statements: `agent_id` (select2 ajax, `/statement/filter/agent/account_name`),
`verb` (select2 multiple), `lms_activity_id` (select2 ajax), `registration` (текст),
`statement_timestamp` (daterangepicker с пресетами «Сегодня», «Вчера», «Последние 7 дней»…).
States: `agent_id`/`activity_iri`/`registration` — текстовые `#text-filter-*`, `state_key` —
select2 без id. Активный фильтр уходит в URL страницы (`?agent_id=["116"]`) и в
`POST …/search?…`; «Сбросить» фильтров — `a.remove_filters_button`, видна только при активном
фильтре (ссылка «Сбросить» рядом с заголовком — сброс состояния DataTables, другое).
Проверено живьём на стенде vshgu2-2420-filters 27.10.2026 (до этого — k8s 14.10)."""
import os
import re

from playwright.sync_api import Locator, Page, expect

from config.environments import Environment
from config.settings import settings
from ui.pages.base_page import BasePage
from ui.pages.login_page import LoginPage


def lrs_base_url(env: Environment) -> str:
    """Хост OpenLRS для окружения: явный `LRS_URL` (приоритет), иначе `env.ui_base_url` с
    `portal-`/`portal.` → `lrs-`/`lrs.` (тот же приём, что и у `_K8S_UI`/хелпдеска —
    config/environments.py:128,134, tests/ui/helpdesk/admin/conftest.py)."""
    explicit = os.getenv("LRS_URL")
    if explicit:
        return explicit.rstrip("/")
    ui = env.ui_base_url.rstrip("/")
    if "://portal-" in ui:
        return ui.replace("://portal-", "://lrs-")
    if "://portal." in ui:
        return ui.replace("://portal.", "://lrs.")
    return ui


class LrsAdminPage(BasePage):
    """Главная панель OpenLRS после входа (боковое меню: Хранилища, Пользователи,
    «Перейти в LMS»)."""

    LOGIN_PATH = "/lrs-admin/login"

    @staticmethod
    def _is_table_search(response) -> bool:
        return response.request.method == "POST" and response.url.split("?")[0].endswith("/search")

    @classmethod
    def login_via_sso(cls, page: Page, env: Environment, email: str, password: str) -> "LrsAdminPage":
        """Вход в LMS формой → переход на callback LRS → ждём `/lrs-admin` в URL. Если
        колбэк оставил форму входа LMS или `invalid_client` (develop без зарегистрированного
        OAuth-клиента), `expect` ниже упадёт таймаутом — исключение не глушим, тест должен
        это увидеть."""
        LoginPage(page).login(email, password, base_url=env.ui_base_url, handle_onboarding=False)
        page.goto(f"{lrs_base_url(env)}/oauth2/auth/callback")
        expect(page).to_have_url(re.compile(r"/lrs-admin"), timeout=settings.UI_TIMEOUT)
        return cls(page)

    def open_login_form(self, env: Environment) -> None:
        self.page.goto(f"{lrs_base_url(env)}{self.LOGIN_PATH}")
        self.wait_loaded()

    def login_with_form(self, email: str, password: str) -> None:
        """Вход через собственную форму OpenLRS — штатно не используется (TC-LRS-015):
        учётки LMS эта форма не принимает, после сабмита остаёмся на ней же."""
        self.page.locator('input[name="email"]').fill(email)
        self.page.locator('input[name="password"]').fill(password)
        self.page.get_by_role("button", name="Войти").click()
        self.wait_loaded()

    def go_to_lms(self) -> Page:
        """Клик «Перейти в LMS» в боковом меню — ссылка на `/admin/programs` LMS с
        `target=_blank` (прогон k8s 14.10): открывается новая вкладка, её и возвращаем.
        Текущая страница остаётся в OpenLRS."""
        with self.page.context.expect_page(timeout=settings.UI_TIMEOUT) as page_info:
            self.page.get_by_role("link", name="Перейти в LMS").click()
        lms_page = page_info.value
        lms_page.wait_for_load_state()
        return lms_page

    def open_stores(self) -> "LrsStoresPage":
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.page.get_by_role("link", name="Хранилища").click()
        self.wait_loaded()
        return LrsStoresPage(self.page)


LMS_LOGS_CHANGES_PATH = "/admin/logs/changes"


def open_lrs_from_logs(page: Page) -> LrsAdminPage:
    """Клик «Перейти в LRS» на уже открытой `/admin/logs/changes` (кнопка-ссылка над
    таблицей, `href` = `<lrs>/oauth2/auth/callback`, `target=_blank`, см. TC-LRS-001; на
    develop кнопки нет — docs/lrs/lrs_recon.md). По прогону k8s 14.10 кнопка есть только
    на вкладке «Изменения» (`/admin/logs/changes`), на `/admin/logs` её нет. OpenLRS
    открывается в новой вкладке — возвращаем page object над ней, исходная вкладка LMS
    остаётся на логах. Отдельная функция, а не метод LMS-страниц: навигация между
    приложениями здесь нужна только со стороны LRS."""
    with page.context.expect_page(timeout=settings.UI_TIMEOUT) as page_info:
        page.get_by_role("link", name="Перейти в LRS").click()
    lrs_page = page_info.value
    lrs_page.wait_for_load_state()
    expect(lrs_page).to_have_url(re.compile(r"/lrs-admin"), timeout=settings.UI_TIMEOUT)
    return LrsAdminPage(lrs_page)


class LrsStoresPage(LrsAdminPage):
    """Список хранилищ `/lrs-admin/store`: Название, Папка, Размер, Количество states,
    Количество statements."""

    PATH = "/lrs-admin/store"
    # Порядок колонок — по разведке (docs/lrs/lrs_recon.md), не проверен живым прогоном.
    _STATEMENTS_COUNT_COLUMN = 4

    def open(self, env: Environment) -> None:
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.page.goto(f"{lrs_base_url(env)}{self.PATH}")
        self.wait_loaded()

    @property
    def table(self) -> Locator:
        return self.page.locator("table.dataTable:has(tbody tr)").first

    def row(self, name: str) -> Locator:
        return self.table.locator(f"tbody tr:has-text('{name}')").first

    def statements_count(self, name: str = "default store"):
        """Значение колонки «Количество statements» строки (TC-LRS-006). Счётчик кэшируется
        и отстаёт от таблицы; при нуле показывается «-» — возвращаем None."""
        text = self.row(name).locator("td").nth(self._STATEMENTS_COUNT_COLUMN).inner_text().strip()
        return int(text) if text.isdigit() else None

    def open_store(self, name: str = "default store") -> "LrsStoreClientsPage":
        """Клик по названию хранилища в строке → переход в «Клиенты хранилища» (store_id
        берётся из итогового URL, без хардкода). Переход делает только ссылка-название:
        клик по самой строке (по ячейке «Папка»/«Размер») ничего не открывает — так
        сложились 8 падений первого прогона на k8s 14.10."""
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(name).get_by_role("link", name=name).first.click()
        self.wait_loaded()
        match = re.search(r"/store/(\d+)/client", self.page.url)
        store_id = int(match.group(1)) if match else 1
        return LrsStoreClientsPage(self.page, store_id=store_id)


class LrsStoreSectionPage(LrsAdminPage):
    """База для разделов внутри хранилища (`/lrs-admin/store/{id}/<раздел>`): клиенты,
    statements, states, agents."""

    SECTION = ""

    def __init__(self, page: Page, store_id: int = 1):
        super().__init__(page)
        self.store_id = store_id

    @property
    def path(self) -> str:
        return f"/lrs-admin/store/{self.store_id}/{self.SECTION}"

    def open(self, env: Environment) -> int:
        """Открыть раздел и дождаться ответа DataTables. Возвращает `recordsTotal` из
        ответа — пригодится для сверки со счётчиком на /lrs-admin/store (TC-LRS-006)."""
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT) as resp_info:
            self.page.goto(f"{lrs_base_url(env)}{self.path}")
        self.wait_loaded()
        return resp_info.value.json().get("recordsTotal")

    @property
    def table(self) -> Locator:
        return self.page.locator("table.dataTable:has(tbody tr)").first

    def row(self, index: int = 0) -> Locator:
        return self.table.locator("tbody tr").nth(index)

    @property
    def data_rows(self) -> Locator:
        """Строки таблицы без заглушки «Совпадений не найдено» (DataTables рисует её тоже
        как `tbody tr`, с одной ячейкой `td.dt-empty`/`dataTables_empty`)."""
        return self.table.locator("tbody tr:has(td:nth-child(2))")

    def _filter(self, name: str) -> Locator:
        return self.page.locator(f"li[filter-name='{name}']")

    def open_filter(self, name: str) -> Locator:
        """Раскрыть dropdown фильтра `li[filter-name=name]` (если ещё не раскрыт) и вернуть
        его `li` — виджет внутри кликабелен только после этого."""
        li = self._filter(name)
        menu = li.locator(".dropdown-menu")
        if not menu.is_visible():
            li.locator("a.dropdown-toggle").click()
            expect(menu).to_be_visible(timeout=settings.UI_TIMEOUT)
        return li

    def filter_by_select2(self, name: str, text: str, option_text: str | None = None) -> None:
        """Фильтры-select2 (с ajax-поиском и без): раскрыть, напечатать `text` в поле поиска,
        дождаться опции и выбрать. Backpack применяет фильтр с задержкой (`filter-debounce`
        1000 мс) — ждём именно `POST …/search`."""
        li = self.open_filter(name)
        li.locator(".select2-search__field").first.click()
        self.page.keyboard.type(text)
        option = self.page.locator(".select2-results__option").filter(has_text=option_text or text).first
        expect(option).to_be_visible(timeout=settings.UI_TIMEOUT)
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            option.click()
        self.wait_loaded()
        self.page.keyboard.press("Escape")

    def select_options(self, name: str) -> list[str]:
        """Тексты `<option>` фильтра-select2 без ajax (`verb`, `state_key`). Список строится из
        кэша агрегатов хранилища (тот же, что даёт «Количество states/statements» в списке
        хранилищ): на свежем хранилище он пуст, пока кэш не обновится (2420, 27.10.2026),
        и select2 показывает «Совпадений не найдено»."""
        li = self._filter(name)
        return [t.strip() for t in li.locator("select option").all_inner_texts() if t.strip() and t.strip() != "-"]

    def filter_by_text(self, name: str, value: str) -> None:
        """Текстовые фильтры (`#text-filter-<key>`): раскрыть, ввести, Enter."""
        li = self.open_filter(name)
        field = li.locator("input[id^='text-filter-']").first
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(value)
            field.press("Enter")
        self.wait_loaded()

    @property
    def reset_filters_button(self) -> Locator:
        """«Сбросить» в панели фильтров — появляется только при активном фильтре."""
        return self.page.locator("a.remove_filters_button")

    def reset_filters(self) -> None:
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.reset_filters_button.click()
        self.wait_loaded()

    def open_lms_user_card(self, link: Locator) -> Page:
        """Ссылки на карточку пользователя LMS (`/admin/users/{id}`) в Statements/Agents/States
        открываются в новой вкладке (`target=_blank`) — возвращаем её."""
        with self.page.context.expect_page(timeout=settings.UI_TIMEOUT) as page_info:
            link.click()
        lms_page = page_info.value
        lms_page.wait_for_load_state()
        return lms_page


class LrsStoreClientsPage(LrsStoreSectionPage):
    """«Клиенты хранилища» (`/lrs-admin/store/{id}/client`): Логин, Пароль, Дата создания,
    Launch, Действия."""

    SECTION = "client"

    def first_launch_href(self, index: int = 0) -> str:
        """`href` ссылки Launch строки — тест парсит из него `endpoint=` и
        `auth=Basic <base64 логин:пароль>` (TC-LRS-007)."""
        return self.row(index).get_by_role("link", name="Launch").get_attribute("href")


class LrsStoreStatementsPage(LrsStoreSectionPage):
    """Statements хранилища (`/lrs-admin/store/{id}/statement`): Agent, Verb, Activity,
    Дата создания, Действия; фильтры agent_id/verb/date, кнопки
    «Предпросмотр»/«Генерация отчета»/«Скачать архив»/«Сбросить» (docs/lrs/lrs_recon.md,
    TC-LRS-008…012)."""

    SECTION = "statement"

    ARCHIVE_PATH = "/store/{store_id}/archive/download"

    def filter_by_agent(self, agent_id) -> None:
        """Фильтр «Agent ID» — select2 с ajax-поиском по `account_name`; после выбора в URL
        `?agent_id=["<id>"]`."""
        self.filter_by_select2("agent_id", str(agent_id))

    def filter_by_verb(self, verb: str) -> None:
        """Фильтр «Verb» — select2 multiple; `verb` — короткое имя (passed), опция ищется по нему."""
        self.filter_by_select2("verb", verb)

    def filter_by_activity(self, activity: str) -> None:
        self.filter_by_select2("lms_activity_id", activity)

    def filter_by_registration(self, registration: str) -> None:
        self.filter_by_text("registration", registration)

    def filter_by_date_preset(self, preset: str = "Сегодня") -> None:
        """Фильтр «Date»: раскрыть dropdown, открыть daterangepicker, выбрать пресет из
        `.daterangepicker .ranges li` («Сегодня», «Вчера», «Последние 7 дней», «Последние
        30 дней», «Текущий месяц», «Последний месяц»)."""
        self.open_filter("statement_timestamp")
        self.page.locator("#daterangepicker-statementTimestamp").click()
        item = self.page.locator(".daterangepicker .ranges li", has_text=preset).first
        expect(item).to_be_visible(timeout=settings.UI_TIMEOUT)
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            item.click()
        self.wait_loaded()

    def open_preview(self, index: int = 0) -> None:
        self.row(index).get_by_role("link", name="Предпросмотр").click()
        self.wait_loaded()

    def open_agent_link(self, index: int = 0) -> Page:
        """Клик по значению Agent строки → карточка пользователя LMS в новой вкладке (TC-LRS-008)."""
        return self.open_lms_user_card(self.row(index).locator("a[href*='/admin/users/']").first)

    def generate_report(self):
        """«Генерация отчета»: JS-кнопка шлёт `POST …/statement/report_generation?<фильтры
        страницы>`; без фильтра даты сервер отвечает 422 (`statement_timestamp` обязателен),
        поэтому перед кликом нужен `filter_by_date_preset`. Возвращает ответ сервера —
        тест сам решает, что считать успехом (TC-LRS-011)."""
        with self.page.expect_response(
            lambda r: r.url.split("?")[0].endswith("/report_generation"), timeout=settings.UI_TIMEOUT
        ) as resp_info:
            self.page.get_by_role("button", name="Генерация отчета").click()
        return resp_info.value

    def archive_url(self, env: Environment, date: str) -> str:
        """`GET <lrs>/store/{id}/archive/download?date=YYYY-MM-DD` (без `/lrs-admin`) — форма
        аккордеона «Скачать архив». Если архива за день нет, сервер отвечает 302 назад."""
        return f"{lrs_base_url(env)}{self.ARCHIVE_PATH.format(store_id=self.store_id)}?date={date}"

    def archive_exists(self, env: Environment, date: str) -> bool:
        response = self.page.request.get(self.archive_url(env, date), max_redirects=0)
        return response.status == 200 and "zip" in response.headers.get("content-type", "")

    def download_archive(self, date: str):
        """«Скачать архив» (TC-LRS-012) — аккордеон с формой «День» (`input#date`, YYYY-MM-DD)
        и кнопкой «Скачать»; возвращает Playwright `Download`."""
        self.page.get_by_role("button", name="Скачать архив").click()
        form = self.page.locator("form[action*='/archive/download']")
        expect(form).to_be_visible(timeout=settings.UI_TIMEOUT)
        form.locator("#date").fill(date)
        with self.page.expect_download(timeout=settings.UI_TIMEOUT) as download_info:
            form.get_by_role("button", name="Скачать").click()
        return download_info.value


class LrsStoreAgentsPage(LrsStoreSectionPage):
    """Agents хранилища (`/lrs-admin/store/{id}/agent`): `account_name` + кнопки
    Statements/State (TC-LRS-010)."""

    SECTION = "agent"

    def account_name(self, index: int = 0) -> str:
        return self.row(index).locator("td").first.inner_text().strip()

    def open_statements_for_row(self, index: int = 0) -> LrsStoreStatementsPage:
        """Ссылка «Statements» строки ведёт на `…/statement?agent_id=<id>` (скаляр, не JSON-массив
        как у виджета) — страница перезагружается и шлёт свой `/search`."""
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(index).get_by_role("link", name="Statements").click()
        self.wait_loaded()
        return LrsStoreStatementsPage(self.page, store_id=self.store_id)

    def open_state_for_row(self, index: int = 0) -> "LrsStoreStatesPage":
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(index).get_by_role("link", name="State").click()
        self.wait_loaded()
        return LrsStoreStatesPage(self.page, store_id=self.store_id)

    def open_account_link(self, index: int = 0) -> Page:
        """Клик по `account_name` строки → карточка пользователя LMS в новой вкладке."""
        return self.open_lms_user_card(self.row(index).locator("a[href*='/admin/users/']").first)


class LrsStoreStatesPage(LrsStoreSectionPage):
    """States хранилища (`/lrs-admin/store/{id}/state`): Agent, State key, Activity IRI,
    Registration; фильтры `agent_id`/`activity_iri`/`registration` (текст) и `state_key`
    (select2) — `FILTER_NAMES` (TC-LRS-014). Появляются от плееров SCORM/xAPI
    (courseditor), тесты конструктора states не пишут."""

    SECTION = "state"

    FILTER_NAMES = ("agent_id", "state_key", "activity_iri", "registration")

    def filter_by_agent(self, agent_id) -> None:
        """На States «ID agent» — текстовый фильтр (`#text-filter-agentId`), не select2."""
        self.filter_by_text("agent_id", str(agent_id))

    def filter_by_state_key(self, state_key: str) -> None:
        self.filter_by_select2("state_key", state_key)

    def filter_by_activity_iri(self, activity_iri: str) -> None:
        self.filter_by_text("activity_iri", activity_iri)

    def filter_by_registration(self, registration: str) -> None:
        self.filter_by_text("registration", registration)

    def open_preview(self, index: int = 0) -> None:
        self.row(index).get_by_role("link", name="Предпросмотр").click()
        self.wait_loaded()
