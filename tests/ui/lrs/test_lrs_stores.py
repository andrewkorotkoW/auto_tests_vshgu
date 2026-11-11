"""UI: хранилища OpenLRS (`/lrs-admin/store*`) — список хранилищ, переход в `default store`,
клиенты хранилища (xAPI-endpoint + Basic-авторизация в Launch-ссылке). Кейсы TC-LRS-006/007
(docs/test_cases/lrs.md), разведка docs/lrs/lrs_recon.md, page object —
ui/pages/lrs_admin_page.py.

Оба теста входят в OpenLRS через SSO (`LrsAdminPage.login_via_sso`), который работает на
k8s и ревью-стендах (develop — SSO работает с 11.11.2026, OAuth-клиент зарегистрирован; до этого `invalid_client`, docs/lrs/lrs_recon.md) —
оба помечены `@pytest.mark.env("develop", "k8s", "stand")`. Эталон UI — стенд vshgu2-2420-filters,
прогон 27.10.2026.

Порядок колонок «Клиенты хранилища»: Логин, Пароль, Дата создания, Launch (подтверждено
27.10). Launch-ссылка — query-строка с `+` вместо пробела (`auth=Basic+Y2xp…%3D`), разбираем
`parse_qs`, а не регуляркой."""
import base64
import re
from urllib.parse import parse_qs, urlparse

import allure
import pytest
import requests
from playwright.sync_api import expect

from config.environments import get_credentials
from config.settings import settings
from ui.pages.lrs_admin_page import LrsAdminPage, LrsStoreStatementsPage, lrs_base_url

_LOGIN_COLUMN = 0
_PASSWORD_COLUMN = 1


@allure.feature("LRS")
@allure.story("Хранилища")
class TestLrsStores:

    @allure.title("UI: список хранилищ и переход в default store совпадает по числу statements")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("develop", "k8s", "stand")
    def test_stores_list_and_open_default_store(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть «Хранилища» — таблица с default store и кнопкой добавления"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)
            stores = lrs.open_stores()
            expect(stores.table).to_be_visible()
            expect(stores.row("default store")).to_be_visible()
            expect(page.get_by_text("Добавить Хранилище")).to_be_visible()
            statements_count = stores.statements_count("default store")

        with allure.step("2. Открыть default store → «Клиенты хранилища»"):
            clients = stores.open_store("default store")
            expect(page).to_have_url(re.compile(rf"/lrs-admin/store/{clients.store_id}/client"))

        with allure.step("3. Вкладка Statements хранилища открывается и отдаёт записи; счётчик списка — число"):
            statements_page = LrsStoreStatementsPage(page, store_id=clients.store_id)
            with page.expect_response(statements_page._is_table_search, timeout=settings.UI_TIMEOUT) as resp_info:
                statements_page.open(env)
            # recordsTotal в /search — размер страницы (k8s 14.10), число записей — recordsFiltered.
            # Сравнивать счётчик списка хранилищ с recordsFiltered нельзя: счётчик — за всё
            # время и кэшируется (2420, 27.10: «6» при 8 statements, «-» при нуле), а таблица
            # открывается с фильтром по дате (daterangepicker, на develop 11.11.2026: 4105 в
            # списке против 11 за сегодня в таблице). Проверяем согласованность по существу:
            # у непустого хранилища счётчик — положительное число и таблица отдаёт записи.
            records = resp_info.value.json().get("recordsFiltered")
            allure.attach(f"список хранилищ: {statements_count!r}, recordsFiltered (с фильтром даты): {records}", "счётчик statements")
            assert isinstance(records, int) and records >= 0, f"recordsFiltered вкладки Statements не число: {records!r}"
            if records > 0:
                assert statements_count is not None and statements_count > 0, (
                    f"Вкладка Statements отдаёт {records} записей, а счётчик в списке хранилищ пуст ({statements_count!r})"
                )

    @allure.title("UI: Launch-ссылка клиента хранилища содержит endpoint и Basic-авторизацию из таблицы")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("develop", "k8s", "stand")
    def test_store_clients_launch_link(self, page, env):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Открыть «Клиенты хранилища» default store"):
            lrs = LrsAdminPage.login_via_sso(page, env, email, password)
            clients = lrs.open_stores().open_store("default store")
            expect(clients.table).to_be_visible()
            expect(page.get_by_text("Добавить Клиент")).to_be_visible()

        with allure.step("2. Разобрать href ссылки Launch: endpoint и Basic-авторизация совпадают со строкой"):
            row = clients.row(0)
            login_cell = row.locator("td").nth(_LOGIN_COLUMN).inner_text().strip()
            password_cell = row.locator("td").nth(_PASSWORD_COLUMN).inner_text().strip()
            href = clients.first_launch_href(0)
            assert href, "Launch-ссылка пуста"

            query = parse_qs(urlparse(href).query)
            endpoint = (query.get("endpoint") or [""])[0]
            auth = (query.get("auth") or [""])[0]
            assert endpoint and auth.startswith("Basic "), f"Не удалось разобрать Launch-ссылку: {href}"
            assert endpoint == f"{lrs_base_url(env)}/xAPI", endpoint

            decoded = base64.b64decode(auth.removeprefix("Basic ")).decode()
            login_from_href, _, password_from_href = decoded.partition(":")
            assert login_from_href == login_cell, (login_from_href, login_cell)
            assert password_from_href == password_cell, (password_from_href, password_cell)

        with allure.step("3. GET {endpoint}/about с Basic-авторизацией клиента отвечает 200 и версией xAPI"):
            response = requests.get(f"{endpoint}/about", auth=(login_from_href, password_from_href), timeout=settings.UI_TIMEOUT / 1000)
            assert response.status_code == 200, response.text[:300]
            body = response.json()
            assert "version" in body, body
