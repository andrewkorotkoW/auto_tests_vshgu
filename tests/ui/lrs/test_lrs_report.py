"""UI/e2e: «Генерация отчета» на вкладке Statements OpenLRS и «Скачать архив» —
связка LRS → LMS «Отчёты» (GET/DELETE /exports, api/endpoints/exports.py). Кейсы
TC-LRS-011/012 (docs/test_cases/lrs.md), разведка docs/lrs/lrs_recon.md («Отчёты»),
page object — ui/pages/lrs_admin_page.py.

Вход в OpenLRS через SSO (`LrsAdminPage.login_via_sso`) штатно работает только на
k8s (develop: OAuth-клиент не зарегистрирован, docs/plans/2026-10-14_lrs_mission.md) —
оба теста помечены `@pytest.mark.env("k8s")`. TC-LRS-011 дополнительно помечен
`@pytest.mark.e2e` — кейс связывает два приложения (LRS и LMS «Отчёты»). Прогоны —
только на k8s после 14:00 14.10.2026 (решение владельца), сейчас только
`pytest --collect-only`.

Отчёт в LMS «Отчёты» (`/admin/reports` или аналог) UI-кейсом не проверяется — страница
не разведана (её нет ни в docs/lrs/lrs_recon.md, ни в существующих page objects), а
угадывать селекторы вслепую рискованно. Шаг 5 TC-LRS-011 покрыт только через API
(GET /exports) — зафиксировано как расхождение с кейсом в отчёте задачи."""
import io
import os
import zipfile

import allure
import openpyxl
import pytest
import requests
from playwright.sync_api import expect

from api.endpoints.exports import ExportsEndpoint
from api.helpers.expectations import expect_status
from config.environments import get_credentials
from config.settings import settings
from ui.pages.lrs_admin_page import LrsAdminPage, LrsStoreStatementsPage
from utils.retry import wait_until


def _login_statements(page, env):
    email, password = get_credentials(env.name, role="admin")
    if not (email and password):
        pytest.skip(f"Нет учётки администратора для {env.name} в .env")
    lrs = LrsAdminPage.login_via_sso(page, env, email, password)
    clients = lrs.open_stores().open_store("default store")
    statements_page = LrsStoreStatementsPage(page, store_id=clients.store_id)
    statements_page.open(env)
    return statements_page


@allure.feature("LRS")
@allure.story("Отчёты")
class TestLrsReport:

    @allure.title("E2E: «Генерация отчета» в LRS → отчёт type=14 в LMS «Отчёты» доходит до completed и скачивается")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.e2e
    @pytest.mark.env("k8s")
    def test_generate_report_appears_in_lms_exports(self, page, env, api_client, lrs_reports_cleanup):
        exports_endpoint = ExportsEndpoint(api_client)

        with allure.step("0. Зафиксировать уже существующие отчёты LRS (type 14) — их не трогаем"):
            existing_ids = {item["id"] for item in exports_endpoint.find_lrs_export()}

        with allure.step("1. На вкладке Statements нажать «Генерация отчета»"):
            statements_page = _login_statements(page, env)
            statements_page.generate_report()

        with allure.step("2. GET /exports (type=14) — появился новый отчёт lrs_statement_export_*"):
            def _new_export():
                candidates = [item for item in exports_endpoint.find_lrs_export() if item["id"] not in existing_ids]
                return candidates[0] if candidates else None

            found = wait_until(lambda: _new_export() is not None, timeout=30, interval=3)
            assert found, "Новый отчёт LRS (type 14) не появился в GET /exports за 30 с после «Генерация отчета»"
            export = _new_export()
            lrs_reports_cleanup.append(export["id"])
            assert export["name"].startswith("lrs_statement_export_"), export["name"]
            assert export["status"] in ("pending", "in_progress"), export

        with allure.step("3. Опрашивать GET /exports до status=completed (не дольше 3 минут)"):
            state = {}

            def _is_completed():
                current = exports_endpoint.list_exports(type=14)
                match = next((item for item in current if item["id"] == export["id"]), None)
                if match:
                    state["export"] = match
                return bool(match) and match.get("status") == "completed"

            completed = wait_until(_is_completed, timeout=180, interval=5)
            assert completed, f"Отчёт {export['id']} не дошёл до completed за 3 минуты: {state.get('export')}"
            completed_export = state["export"]
            assert completed_export.get("download_url"), completed_export

        with allure.step("4. Скачать файл по download_url — ZIP с xlsx, в котором есть строки statements"):
            download_resp = requests.get(completed_export["download_url"], timeout=settings.REQUEST_TIMEOUT)
            expect_status(download_resp, 200)
            archive = zipfile.ZipFile(io.BytesIO(download_resp.content))
            xlsx_names = [name for name in archive.namelist() if name.endswith(".xlsx")]
            assert xlsx_names, f"В архиве отчёта нет xlsx: {archive.namelist()}"
            workbook = openpyxl.load_workbook(io.BytesIO(archive.read(xlsx_names[0])))
            sheet = workbook.active
            assert sheet.max_row >= 2, "В xlsx отчёта нет строк statements (только заголовок или пусто)"

    @allure.title("UI: «Скачать архив» на вкладке Statements")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.env("k8s")
    def test_download_archive(self, page, env):
        with allure.step("1. «Скачать архив» — браузер получает файл-архив ненулевого размера"):
            statements_page = _login_statements(page, env)
            download = statements_page.download_archive()
            path = download.path()
            assert path, "Скачивание «Скачать архив» не вернуло файл"
            assert os.path.getsize(path) > 0, "Скачанный архив пуст"
