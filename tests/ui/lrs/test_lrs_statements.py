"""UI: вкладки Statements/Agents/States хранилища OpenLRS (`/lrs-admin/store/{id}/*`) —
таблица, предпросмотр, фильтры, ссылки в карточку пользователя LMS. Кейсы
TC-LRS-008…010, 014 (docs/test_cases/lrs.md), разведка docs/lrs/lrs_recon.md, page
object — ui/pages/lrs_admin_page.py.

Все тесты входят в OpenLRS через SSO (`LrsAdminPage.login_via_sso`), который штатно
работает только на k8s (develop: OAuth-клиент не зарегистрирован, docs/lrs/lrs_recon.md) —
помечены `@pytest.mark.env("k8s")`. Прогоны — только на k8s после 14:00 14.10.2026
(решение владельца), сейчас только `pytest --collect-only`.

Порядок/индексы колонок (Agent=0, Verb=1, Activity=2, Дата=3) и формат содержимого
предпросмотра/JSON — по разведке docs/lrs/lrs_recon.md, не подтверждены живым прогоном
(SSO на develop сейчас недоступен) — первый прогон на k8s должен это подтвердить или
поправить ниже."""
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


def _login_statements(page, env):
    email, password = get_credentials(env.name, role="admin")
    if not (email and password):
        pytest.skip(f"Нет учётки администратора для {env.name} в .env")
    lrs = LrsAdminPage.login_via_sso(page, env, email, password)
    clients = lrs.open_stores().open_store("default store")
    return LrsStoreStatementsPage(page, store_id=clients.store_id), clients.store_id


@allure.feature("LRS")
@allure.story("Statements/Agents/States")
class TestLrsStatements:

    @allure.title("UI: таблица Statements, предпросмотр записи, ссылка Agent в карточку пользователя LMS")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_statements_table_preview_and_agent_link(self, page, env):
        with allure.step("1. Открыть Statements — таблица с записями и кнопками"):
            statements_page, _ = _login_statements(page, env)
            statements_page.open(env)
            expect(statements_page.table).to_be_visible()
            row = statements_page.row(0)
            expect(row).to_be_visible()
            agent_value = row.locator("td").nth(_AGENT_COLUMN).inner_text().strip()
            assert agent_value, "Agent первой записи пуст"
            expect(page.get_by_role("button", name="Скачать архив")).to_be_visible()
            expect(page.get_by_role("button", name="Генерация отчета")).to_be_visible()
            expect(page.get_by_role("button", name="Сбросить")).to_be_visible()

        with allure.step("2. Предпросмотр первой записи — Agent/Verb/Activity и JSON statement согласованы с таблицей"):
            statements_page.open_preview(0)
            expect(page).to_have_url(re.compile(r"/statement/\d+/show"), timeout=settings.UI_TIMEOUT)
            body_text = page.locator("body").inner_text()
            assert agent_value in body_text, f"Agent {agent_value} не найден на странице предпросмотра"
            assert "adlnet.gov/expapi/verbs" in body_text, "В payload нет verb.id с adlnet.gov/expapi/verbs"
            expect(page.get_by_role("link", name="Вернуться к списку")).to_be_visible()

        with allure.step("3. Вернуться к списку и перейти по значению Agent в карточку пользователя LMS"):
            statements_page.open(env)
            statements_page.open_agent_link(0)
            expect(page).to_have_url(re.compile(rf"/admin/users/{re.escape(agent_value)}"), timeout=settings.UI_TIMEOUT)

    @allure.title("UI: фильтры Statements — Agent ID, Verb, Date и «Сбросить»")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_statements_filters(self, page, env):
        statements_page, _ = _login_statements(page, env)

        with allure.step("1. Фильтр «Agent ID» — только записи выбранного агента"):
            records_total = statements_page.open(env)
            agent_value = statements_page.row(0).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
            with page.expect_response(statements_page._is_table_search) as resp_info:
                statements_page.filter_by_agent(agent_value)
            filtered = resp_info.value.json()
            assert filtered.get("recordsFiltered", 0) <= filtered.get("recordsTotal", 0), filtered
            rows = statements_page.table.locator("tbody tr")
            for i in range(rows.count()):
                cell = rows.nth(i).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
                assert cell == agent_value, f"Строка {i} относится к другому Agent: {cell}"

        with allure.step("2. Фильтр «Verb» = passed — только записи с этим verb"):
            statements_page.filter_by_verb("passed")
            rows = statements_page.table.locator("tbody tr")
            for i in range(rows.count()):
                verb_cell = rows.nth(i).locator("td").nth(_VERB_COLUMN).inner_text().strip().lower()
                assert "passed" in verb_cell, f"Строка {i}: verb {verb_cell} не содержит passed"

        with allure.step("3. Фильтр «Date» — сегодняшняя дата"):
            today = datetime.now().strftime("%d.%m.%Y")
            statements_page.filter_by_date(f"{today} - {today}")
            rows = statements_page.table.locator("tbody tr")
            for i in range(rows.count()):
                date_cell = rows.nth(i).locator("td").nth(_DATE_COLUMN).inner_text().strip()
                assert today in date_cell, f"Строка {i}: дата {date_cell} не содержит {today}"

        with allure.step("4. «Сбросить» — recordsTotal как до фильтрации"):
            with page.expect_response(statements_page._is_table_search) as reset_resp:
                statements_page.reset_filters()
            assert reset_resp.value.json().get("recordsTotal") == records_total

    @allure.title("UI: вкладка Agents — ссылки Statements/State по агенту и переход в карточку LMS")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
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
            account_name = agents_page.account_name(0)
            assert account_name, "account_name первой строки пуст"

        with allure.step("2. Statements агента — только его записи"):
            statements_page = agents_page.open_statements_for_row(0)
            rows = statements_page.table.locator("tbody tr")
            for i in range(rows.count()):
                cell = rows.nth(i).locator("td").nth(_AGENT_COLUMN).inner_text().strip()
                assert cell == account_name, f"Строка {i}: Agent {cell} != {account_name}"

        with allure.step("3. Клик по account_name — карточка пользователя LMS"):
            agents_page = LrsStoreAgentsPage(page, store_id=clients.store_id)
            agents_page.open(env)
            agents_page.open_account_link(0)
            expect(page).to_have_url(re.compile(rf"/admin/users/{re.escape(account_name)}"), timeout=settings.UI_TIMEOUT)

    @allure.title("UI: вкладка States — таблица, ссылка Agent в карточку LMS, предпросмотр")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
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
            for filter_id in ("#filter_agentId", "#filter_stateKey", "#filter_activityIri", "#filter_registration"):
                assert page.locator(filter_id).count() > 0, f"Не найден фильтр {filter_id}"

        with allure.step("2. Предпросмотр state — страница с содержимым"):
            states_page.open_preview(0)
            expect(page).to_have_url(re.compile(r"/state/\d+/show"), timeout=settings.UI_TIMEOUT)

        with allure.step("3. Вернуться к списку и перейти по Agent в карточку пользователя LMS"):
            states_page = LrsStoreStatesPage(page, store_id=clients.store_id)
            states_page.open(env)
            with page.expect_navigation():
                states_page.row(0).locator("a[href*='/admin/users/']").first.click()
            states_page.wait_loaded()
            expect(page).to_have_url(re.compile(r"/admin/users/\d+"), timeout=settings.UI_TIMEOUT)
