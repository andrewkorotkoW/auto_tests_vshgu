"""UI: вкладки Statements/Agents/States хранилища OpenLRS (`/lrs-admin/store/{id}/*`) —
таблица, предпросмотр, фильтры, ссылки в карточку пользователя LMS. Кейсы
TC-LRS-008…010, 014 (docs/test_cases/lrs.md), разведка docs/lrs/lrs_recon.md, page
object — ui/pages/lrs_admin_page.py.

Все тесты входят в OpenLRS через SSO (`LrsAdminPage.login_via_sso`), который работает на
k8s и ревью-стендах (develop: OAuth-клиент не зарегистрирован, docs/lrs/lrs_recon.md) —
помечены `@pytest.mark.env("k8s", "stand")`. Эталон UI — стенд vshgu2-2420-filters, прогон
27.10.2026 (k8s выведен). Statements на стенде появляются от e2e-теста
tests/e2e/lrs/test_statement_after_test_pass.py — на свежем стенде таблица пуста, тесты
ниже это учитывают (`pytest.skip`), а не падают на пустой таблице.

Индексы колонок: Agent=0, Verb=1, Activity=2, Дата=3 (подтверждено 27.10). Известные
дефекты ветки 2420 помечены `pytest.xfail` в конце соответствующего теста, чтобы остальные
шаги проверялись. Список verb в фильтре и счётчики в списке хранилищ — из кэша агрегатов,
который отстаёт от таблицы (на свежем хранилище пуст) — тест фильтра Verb тогда скипается."""
import re
from datetime import datetime

import allure
import pytest
from playwright.sync_api import expect

from config.environments import get_credentials
from config.settings import settings
from ui.pages.lrs_admin_page import (
    LrsAdminPage,
    LrsStoreAgentsPage,
    LrsStoreStatementsPage,
    LrsStoreStatesPage,
)

_AGENT_COLUMN = 0
_VERB_COLUMN = 1
_DATE_COLUMN = 3

_MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def _today_russian() -> str:
    """Дата в колонке «Дата создания statement-а» — «27 октября 2026, 18:32:00»."""
    now = datetime.now()
    return f"{now.day} {_MONTHS_RU[now.month - 1]} {now.year}"


def _login_statements(page, env):
    email, password = get_credentials(env.name, role="admin")
    if not (email and password):
        pytest.skip(f"Нет учётки администратора для {env.name} в .env")
    lrs = LrsAdminPage.login_via_sso(page, env, email, password)
    clients = lrs.open_stores().open_store("default store")
    return LrsStoreStatementsPage(page, store_id=clients.store_id), clients.store_id


def _require_rows(section_page, what: str) -> None:
    """Таблица без записей — не дефект стенда: statements/states пишут плееры, на свежем
    стенде их нет, пока не прошёл e2e-тест конструктора (states — только SCORM/xAPI)."""
    if section_page.data_rows.count() == 0:
        pytest.skip(f"На стенде нет {what} в default store — нечего проверять")


@allure.feature("LRS")
@allure.story("Statements/Agents/States")
class TestLrsStatements:

    @allure.title("UI: таблица Statements, предпросмотр записи, ссылка Agent в карточку пользователя LMS")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s", "stand")
    def test_statements_table_preview_and_agent_link(self, page, env):
        with allure.step("1. Открыть Statements — таблица с записями и кнопками"):
            statements_page, _ = _login_statements(page, env)
            statements_page.open(env)
            expect(statements_page.table).to_be_visible()
            _require_rows(statements_page, "statements")
            row = statements_page.row(0)
            expect(row).to_be_visible()
            agent_value = row.locator("td").nth(_AGENT_COLUMN).inner_text().strip()
            assert agent_value, "Agent первой записи пуст"
            expect(page.get_by_role("button", name="Скачать архив")).to_be_visible()
            expect(page.get_by_role("button", name="Генерация отчета")).to_be_visible()
            # «Сбросить» рядом с заголовком — ссылка сброса состояния DataTables (не фильтров)
            expect(page.get_by_role("link", name="Сбросить").first).to_be_visible()

        with allure.step("2. Предпросмотр первой записи — Agent/Verb/Activity и JSON statement согласованы с таблицей"):
            statements_page.open_preview(0)
            expect(page).to_have_url(re.compile(r"/statement/\d+/show"), timeout=settings.UI_TIMEOUT)
            body_text = page.locator("body").inner_text()
            assert agent_value in body_text, f"Agent {agent_value} не найден на странице предпросмотра"
            assert "adlnet.gov/expapi/verbs" in body_text, "В payload нет verb.id с adlnet.gov/expapi/verbs"
            expect(page.get_by_role("link", name="Вернуться к списку")).to_be_visible()

        with allure.step("3. Вернуться к списку и перейти по значению Agent в карточку пользователя LMS (новая вкладка)"):
            statements_page.open(env)
            lms_page = statements_page.open_agent_link(0)
            expect(lms_page).to_have_url(re.compile(rf"/admin/users/{re.escape(agent_value)}"), timeout=settings.UI_TIMEOUT)

    @allure.title("UI: фильтры Statements — Agent ID, Verb, Date и «Сбросить»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s", "stand")
    def test_statements_filters(self, page, env):
        statements_page, _ = _login_statements(page, env)

        with allure.step("1. Фильтр «Agent ID» — только записи выбранного агента, в URL agent_id"):
            records_total = statements_page.open(env)
            _require_rows(statements_page, "statements")
            agent_value = statements_page.row(0).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
            statements_page.filter_by_agent(agent_value)
            expect(page).to_have_url(re.compile(r"[?&]agent_id="), timeout=settings.UI_TIMEOUT)
            rows = statements_page.data_rows
            assert rows.count() > 0, "После фильтра по Agent ID таблица пуста"
            for i in range(rows.count()):
                cell = rows.nth(i).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
                assert cell == agent_value, f"Строка {i} относится к другому Agent: {cell}"

        with allure.step("2. Фильтр «Date» — пресет «Сегодня» (в URL statement_timestamp), даты строк сегодняшние"):
            statements_page.filter_by_date_preset("Сегодня")
            expect(page).to_have_url(re.compile(r"statement_timestamp="), timeout=settings.UI_TIMEOUT)
            today_label = _today_russian()
            rows = statements_page.data_rows
            for i in range(rows.count()):
                date_cell = rows.nth(i).locator("td").nth(_DATE_COLUMN).inner_text().strip()
                assert date_cell.startswith(today_label), f"Строка {i}: дата {date_cell} не сегодняшняя ({today_label})"

        with allure.step("3. «Сбросить» в панели фильтров — URL без фильтров, recordsTotal как до фильтрации"):
            expect(statements_page.reset_filters_button).to_be_visible()
            with page.expect_response(statements_page._is_table_search) as reset_resp:
                statements_page.reset_filters()
            assert reset_resp.value.json().get("recordsTotal") == records_total
            assert "agent_id=" not in page.url and "statement_timestamp=" not in page.url, page.url
            expect(statements_page.reset_filters_button).to_be_hidden()

        with allure.step("4. Фильтр «Verb» = passed — только записи с этим verb"):
            if not statements_page.select_options("verb"):
                pytest.skip(
                    "Список verb в фильтре строится из кэша агрегатов хранилища и на свежем "
                    "хранилище пуст, пока кэш не обновится (2420, 27.10.2026) — фильтр проверить нельзя"
                )
            statements_page.filter_by_verb("passed")
            rows = statements_page.data_rows
            for i in range(rows.count()):
                verb_cell = rows.nth(i).locator("td").nth(_VERB_COLUMN).inner_text().strip().lower()
                assert "passed" in verb_cell, f"Строка {i}: verb {verb_cell} не содержит passed"

    @allure.title("UI: вкладка Agents — ссылки Statements/State по агенту и переход в карточку LMS")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s", "stand")
    def test_agents_tab_links(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть Agents — колонка account_name, кнопки Statements/State"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)
            clients = lrs.open_stores().open_store("default store")
            agents_page = LrsStoreAgentsPage(page, store_id=clients.store_id)
            agents_page.open(env)
            expect(agents_page.table).to_be_visible()
            _require_rows(agents_page, "агентов (statements)")
            account_name = agents_page.account_name(0)
            assert account_name, "account_name первой строки пуст"

        with allure.step("2. Клик по account_name — карточка пользователя LMS (новая вкладка)"):
            lms_page = agents_page.open_account_link(0)
            expect(lms_page).to_have_url(re.compile(rf"/admin/users/{re.escape(account_name)}"), timeout=settings.UI_TIMEOUT)
            lms_page.close()

        with allure.step("3. Statements агента — страница с ?agent_id, только его записи"):
            statements_page = agents_page.open_statements_for_row(0)
            expect(page).to_have_url(re.compile(rf"/statement\?agent_id={re.escape(account_name)}"), timeout=settings.UI_TIMEOUT)
            rows = statements_page.data_rows
            assert rows.count() > 0, "Statements агента пусты"
            foreign = [
                rows.nth(i).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
                for i in range(rows.count())
                if rows.nth(i).locator("td").nth(_AGENT_COLUMN).inner_text().strip() != account_name
            ]
            if foreign:
                pytest.xfail(
                    "Дефект ветки 2420-filters (27.10.2026): ссылка «Statements» с вкладки Agents "
                    f"передаёт ?agent_id={account_name} скаляром, фильтр не применяется — в таблице "
                    f"чужие агенты {sorted(set(foreign))}; виджет пишет agent_id=[\"id\"] и работает"
                )

    @allure.title("UI: вкладка States — таблица, ссылка Agent в карточку LMS, предпросмотр")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s", "stand")
    def test_states_tab(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть States — таблица и фильтры по agent/stateKey/activityIri/registration"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)
            clients = lrs.open_stores().open_store("default store")
            states_page = LrsStoreStatesPage(page, store_id=clients.store_id)
            states_page.open(env)
            expect(states_page.table).to_be_visible()
            for name in states_page.FILTER_NAMES:
                assert page.locator(f"li[filter-name='{name}']").count() > 0, f"Не найден фильтр {name}"
            _require_rows(states_page, "states (их пишут плееры SCORM/xAPI, не конструктор)")

        with allure.step("2. Предпросмотр state — страница с содержимым"):
            states_page.open_preview(0)
            expect(page).to_have_url(re.compile(r"/state/\d+/show"), timeout=settings.UI_TIMEOUT)

        with allure.step("3. Вернуться к списку и перейти по Agent в карточку пользователя LMS (новая вкладка)"):
            states_page = LrsStoreStatesPage(page, store_id=clients.store_id)
            states_page.open(env)
            lms_page = states_page.open_lms_user_card(states_page.row(0).locator("a[href*='/admin/users/']").first)
            expect(lms_page).to_have_url(re.compile(r"/admin/users/\d+"), timeout=settings.UI_TIMEOUT)
