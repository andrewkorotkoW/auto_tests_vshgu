"""E2E: слушатель проходит SCORM-курс (инд. обучение) → в OpenLRS появляются statements
initialized/launched/responded/passed/completed и state активности для его Agent. Кейс TC-LRS-016
(docs/test_cases/lrs.md). Прохождение — tests/ui/courses/scorm/scorm_flow.py, LRS — ui/pages/lrs_admin_page.py.

Вход в OpenLRS через SSO работает на k8s и ревью-стендах (develop: `invalid_client`) — `env("k8s","stand")`.
Разведка 2420 (27.10.2026): драйвер SCORM шлёт в `POST /xAPI/statements` statement `passed` с
`result.score.raw = 0`, хотя SCORM API отдаёт `cmi.score.raw = 100` и `cmi.score.scaled = 1` —
кандидат в дефект конвертации SCORM → xAPI, проверяется последним шагом (xfail)."""
import re

import allure
import pytest
from playwright.sync_api import expect

from api.endpoints.tincan import TincanEndpoint
from config.environments import get_credentials
from config.settings import settings
from ui.pages.login_page import LoginPage
from ui.pages.lrs_admin_page import LrsAdminPage, LrsStoreStatementsPage, LrsStoreStatesPage
from ui.pages.scorm_page import ScormCoursePage
from ui.pages.user_sidebar_page import UserSidebarPage
from tests.ui.courses.scorm.scorm_flow import EXPECTED_VERBS, create_scorm_course, pass_scorm_and_verify
from utils.retry import wait_until

_VERB_COLUMN = 1


@allure.feature("LRS")
@allure.story("Сквозной сценарий: SCORM → statements и state")
class TestLrsScormFlow:

    @allure.title("E2E: слушатель проходит SCORM-курс → в LRS statements passed/completed и state его Agent")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.e2e
    @pytest.mark.env("k8s", "stand")
    def test_scorm_pass_creates_statements_and_state(self, browser, env, api_client, prepared_user):
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")
        tincan_ep = TincanEndpoint(api_client)

        with allure.step("1. API: слушатель, курс SCORM 2004, назначение на инд. трек"):
            student = prepared_user()
            course = create_scorm_course(tincan_ep, prefix="Автотест_LRS_SCORM")
            assert tincan_ep.assign_activities([course["id"]], [student["id"]])

        try:
            with allure.step("2. Слушатель проходит курс в UI (плеер, SCORM API, xAPI, «Повторить»)"):
                student_context = browser.new_context(viewport={"width": 1366, "height": 768})
                student_page = student_context.new_page()
                try:
                    LoginPage(student_page).login(student["email"], student["password"], base_url=env.ui_base_url)
                    UserSidebarPage(student_page).dismiss_popups()
                    course_page = ScormCoursePage(student_page)
                    course_page.open_individual_course(course["name"])
                    player = pass_scorm_and_verify(course_page, course)
                    passed_statement = player.statement("passed")
                finally:
                    student_context.close()

            admin_context = browser.new_context(viewport={"width": 1366, "height": 768})
            admin_page = admin_context.new_page()
            try:
                with allure.step("3. admin в OpenLRS: Statements с фильтром Agent ID = id слушателя — все verbs прохождения (ретраи до 60 с)"):
                    lrs = LrsAdminPage.login_via_sso(admin_page, env, email, password)
                    clients = lrs.open_stores().open_store("default store")
                    statements_page = LrsStoreStatementsPage(admin_page, store_id=clients.store_id)
                    seen: set = set()

                    def _all_verbs_in_lrs() -> bool:
                        try:
                            statements_page.open(env)
                            statements_page.filter_by_agent(student["id"])
                        except Exception:  # noqa: BLE001 — агента ещё нет в выпадашке
                            return False
                        rows = statements_page.data_rows
                        seen.clear()
                        seen.update(rows.nth(i).locator("td").nth(_VERB_COLUMN).inner_text().strip().lower() for i in range(rows.count()))
                        return EXPECTED_VERBS <= seen

                    assert wait_until(_all_verbs_in_lrs, timeout=60, interval=5), (
                        f"За 60 с в Statements агента {student['id']} нет {sorted(EXPECTED_VERBS - seen)}; есть {sorted(seen)}"
                    )

                with allure.step("4. Предпросмотр statement passed — actor.account.name = id слушателя, object = курс"):
                    statements_page.table.locator("tbody tr", has_text="passed").first.get_by_role("link", name="Предпросмотр").click()
                    expect(admin_page).to_have_url(re.compile(r"/statement/\d+/show"), timeout=settings.UI_TIMEOUT)
                    body_text = admin_page.locator("body").inner_text()
                    assert f'"name": "{student["id"]}"' in body_text, "В JSON statement нет actor.account.name = id слушателя"
                    assert f"/content/{course['id']}" in body_text, "В JSON statement object.id не ссылается на курс"

                with allure.step("5. Вкладка States: у агента есть state активности (PUT /xAPI/activities/state)"):
                    states_page = LrsStoreStatesPage(admin_page, store_id=clients.store_id)
                    states_page.open(env)
                    states_page.filter_by_agent(student["id"])
                    assert states_page.data_rows.count() >= 1, "У агента нет state в OpenLRS"

                with allure.step("6. Счёт в statement passed совпадает со SCORM (cmi.score.raw = 100)"):
                    raw = (passed_statement.get("result") or {}).get("score", {}).get("raw")
                    if raw != 100:
                        pytest.xfail(
                            "Кандидат в дефект (2420, 27.10.2026): драйвер SCORM шлёт statement passed с "
                            f"result.score.raw = {raw}, хотя cmi.score.raw = 100 / cmi.score.scaled = 1"
                        )
            finally:
                admin_context.close()
        finally:
            tincan_ep.mass_delete([course["id"]])
