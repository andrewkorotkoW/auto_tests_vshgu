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

Фильтры Statements/States (`filter_agentId`, `filter_verb`, `filter_lmsActivityId`,
`daterangepicker-statementTimestamp` и т.п., docs/lrs/lrs_recon.md) собраны по описанию
разведки без живой проверки на develop (SSO там сейчас недоступен) — точный тип виджета
(select2 с поиском/обычный select/текстовое поле с датапикером) уточнится первым прогоном
на k8s."""
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

    def go_to_lms(self) -> None:
        """Клик «Перейти в LMS» в боковом меню — обычная ссылка на главную LMS без
        авторизации (docs/lrs/lrs_recon.md)."""
        with self.page.expect_navigation():
            self.page.get_by_role("link", name="Перейти в LMS").click()
        self.wait_loaded()

    def open_stores(self) -> "LrsStoresPage":
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.page.get_by_role("link", name="Хранилища").click()
        self.wait_loaded()
        return LrsStoresPage(self.page)


def open_lrs_from_logs(page: Page) -> LrsAdminPage:
    """Клик «Перейти в LRS» на уже открытой `/admin/logs` (кнопка-ссылка над таблицей,
    `href` = `<lrs>/oauth2/auth/callback`, см. TC-LRS-001; на develop кнопки нет —
    docs/lrs/lrs_recon.md). Отдельная функция, а не метод LMS-страниц: навигация между
    приложениями здесь нужна только со стороны LRS."""
    with page.expect_navigation():
        page.get_by_role("link", name="Перейти в LRS").click()
    expect(page).to_have_url(re.compile(r"/lrs-admin"), timeout=settings.UI_TIMEOUT)
    return LrsAdminPage(page)


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

    def statements_count(self, name: str = "default store") -> int:
        """Значение колонки «Количество statements» строки — для сверки с `recordsTotal`
        вкладки Statements (TC-LRS-006)."""
        return int(self.row(name).locator("td").nth(self._STATEMENTS_COUNT_COLUMN).inner_text().strip())

    def open_store(self, name: str = "default store") -> "LrsStoreClientsPage":
        """Клик по строке хранилища → переход в «Клиенты хранилища» (store_id берётся из
        итогового URL, без хардкода)."""
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(name).click()
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

    def reset_filters(self) -> None:
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.page.get_by_role("button", name="Сбросить").click()
        self.wait_loaded()


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

    def filter_by_agent(self, agent_id) -> None:
        """Фильтр «Agent ID» (`filter_agentId`, select2 с поиском по разведке)."""
        combobox = self.page.locator("#filter_agentId").locator("xpath=..").get_by_role("combobox").first
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            combobox.click()
            option = self.page.get_by_role("option", name=str(agent_id))
            expect(option).to_be_visible(timeout=settings.UI_TIMEOUT)
            option.click()

    def filter_by_verb(self, verb: str) -> None:
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.page.locator("#filter_verb").select_option(verb)

    def filter_by_activity(self, activity_iri: str) -> None:
        field = self.page.locator("#filter_lmsActivityId")
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(activity_iri)
            field.press("Enter")

    def filter_by_date(self, date_range: str) -> None:
        """`date_range` — текст в формате daterangepicker, например
        `«ДД.MM.ГГГГ - ДД.MM.ГГГГ»`."""
        field = self.page.locator("#daterangepicker-statementTimestamp")
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(date_range)
            field.press("Enter")

    def open_preview(self, index: int = 0) -> None:
        self.row(index).get_by_role("link", name="Предпросмотр").click()
        self.wait_loaded()

    def open_agent_link(self, index: int = 0) -> None:
        """Клик по значению Agent строки → карточка пользователя LMS (TC-LRS-008)."""
        with self.page.expect_navigation():
            self.row(index).locator("a[href*='/admin/users/']").first.click()
        self.wait_loaded()

    def generate_report(self) -> None:
        """«Генерация отчета»: ставит задачу `…/statement/report_generation`, отчёт
        появляется в LMS «Отчёты» (TC-LRS-011) — проверка результата вне этой страницы."""
        self.page.get_by_role("button", name="Генерация отчета").click()

    def download_archive(self):
        """«Скачать архив» (TC-LRS-012): возвращает Playwright `Download`."""
        with self.page.expect_download(timeout=settings.UI_TIMEOUT) as download_info:
            self.page.get_by_role("button", name="Скачать архив").click()
        return download_info.value


class LrsStoreAgentsPage(LrsStoreSectionPage):
    """Agents хранилища (`/lrs-admin/store/{id}/agent`): `account_name` + кнопки
    Statements/State (TC-LRS-010)."""

    SECTION = "agent"

    def account_name(self, index: int = 0) -> str:
        return self.row(index).locator("td").first.inner_text().strip()

    def open_statements_for_row(self, index: int = 0) -> LrsStoreStatementsPage:
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(index).get_by_role("link", name="Statements").click()
        self.wait_loaded()
        return LrsStoreStatementsPage(self.page, store_id=self.store_id)

    def open_state_for_row(self, index: int = 0) -> "LrsStoreStatesPage":
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            self.row(index).get_by_role("link", name="State").click()
        self.wait_loaded()
        return LrsStoreStatesPage(self.page, store_id=self.store_id)

    def open_account_link(self, index: int = 0) -> None:
        """Клик по `account_name` строки → карточка пользователя LMS."""
        with self.page.expect_navigation():
            self.row(index).locator("a[href*='/admin/users/']").first.click()
        self.wait_loaded()


class LrsStoreStatesPage(LrsStoreSectionPage):
    """States хранилища (`/lrs-admin/store/{id}/state`): Agent, State key, Activity IRI,
    Registration; фильтры по agent/stateKey/activityIri/registration (TC-LRS-014)."""

    SECTION = "state"

    def filter_by_agent(self, agent_id) -> None:
        combobox = self.page.locator("#filter_agentId").locator("xpath=..").get_by_role("combobox").first
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            combobox.click()
            option = self.page.get_by_role("option", name=str(agent_id))
            expect(option).to_be_visible(timeout=settings.UI_TIMEOUT)
            option.click()

    def filter_by_state_key(self, state_key: str) -> None:
        field = self.page.locator("#filter_stateKey")
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(state_key)
            field.press("Enter")

    def filter_by_activity_iri(self, activity_iri: str) -> None:
        field = self.page.locator("#filter_activityIri")
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(activity_iri)
            field.press("Enter")

    def filter_by_registration(self, registration: str) -> None:
        field = self.page.locator("#filter_registration")
        with self.page.expect_response(self._is_table_search, timeout=settings.UI_TIMEOUT):
            field.fill(registration)
            field.press("Enter")

    def open_preview(self, index: int = 0) -> None:
        self.row(index).get_by_role("link", name="Предпросмотр").click()
        self.wait_loaded()
