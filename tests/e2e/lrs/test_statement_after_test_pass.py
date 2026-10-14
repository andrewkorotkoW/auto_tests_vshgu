"""E2E: слушатель проходит назначенный тест в LMS → в LRS (OpenLRS) появляется
statement с его id (Agent). Кейс TC-LRS-013 (docs/test_cases/lrs.md), разведка
docs/lrs/lrs_recon.md («Откуда берутся statements») — на k8s плеер конструктора
тестов шлёт xAPI в `default store` при прохождении теста, Agent = id пользователя LMS.

Два независимых браузерных контекста (как в tests/ui/p2p/test_peer_review.py):
слушатель проходит тест обычной формой входа LMS, admin — через SSO в OpenLRS
(`LrsAdminPage.login_via_sso`). Назначение теста слушателю и его прохождение в UI —
тот же приём, что в tests/ui/proctoring/individual/test_proctoring_flow.py
(`AssignmentsEndpoint.assign_to_individual` + «Индивидуальное обучение» → «Курсы и
тесты»), но без прокторинга — обычный тест с одним вопросом конструктора.

SSO в OpenLRS штатно работает только на k8s (develop: OAuth-клиент не зарегистрирован,
docs/plans/2026-10-14_lrs_mission.md) — тест помечен `@pytest.mark.env("k8s")`.
Прогоны — только на k8s после 14:00 14.10.2026 (решение владельца), сейчас только
`pytest --collect-only`."""
import allure
import pytest
from playwright.sync_api import expect

from api.endpoints.assignments import AssignmentsEndpoint
from api.endpoints.tests import TestsEndpoint
from api.helpers.data_generator import generate_constructor_question_payload, generate_single_choice_answers
from config.environments import get_credentials
from config.settings import settings
from ui.pages.login_page import LoginPage
from ui.pages.lrs_admin_page import LrsAdminPage, LrsStoreAgentsPage, LrsStoreStatementsPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.retry import wait_until

_CORRECT_ANSWER = "Автотест_LRS_ВерныйОтвет"
_WRONG_ANSWER = "Автотест_LRS_НеверныйОтвет"


@allure.feature("LRS")
@allure.story("Сквозной сценарий: прохождение теста → statement")
class TestLrsStatementFlow:

    @allure.title("E2E: слушатель проходит тест → в LRS появляется statement с его id")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.lrs
    @pytest.mark.e2e
    @pytest.mark.env("k8s")
    def test_passed_test_creates_statements(self, browser, env, api_client, prepared_user, created_test):
        tests_ep = TestsEndpoint(api_client)
        email, password = get_credentials(env.name, role="admin")
        if not (email and password):
            pytest.skip(f"Нет учётки администратора для {env.name} в .env")

        with allure.step("1. Подготовить слушателя и тест с одним вопросом, назначить индивидуально"):
            student = prepared_user()
            test = created_test()

            questions = tests_ep.get_questions(test["id"])
            assert questions, f"У теста id={test['id']} не найден дефолтный вопрос"
            default_question = questions[0]
            group_id = int(default_question["group"]["group_id"])
            payload = generate_constructor_question_payload(
                question_text="Автотест_LRS_Вопрос",
                answers=generate_single_choice_answers(_CORRECT_ANSWER, _WRONG_ANSWER),
                question_id=default_question["question_id"],
                group_id=group_id,
                order=1,
            )
            tests_ep.create_question(test["id"], payload)

            AssignmentsEndpoint(api_client).assign_to_individual([test["id"]], [student["id"]])

        try:
            with allure.step("2. Слушатель проходит тест в UI до экрана результата"):
                student_context = browser.new_context(viewport={"width": 1366, "height": 768})
                student_page = student_context.new_page()
                try:
                    LoginPage(student_page).login(student["email"], student["password"], base_url=env.ui_base_url)
                    UserSidebarPage(student_page).dismiss_popups()

                    # Плеер открываем напрямую по content_id, как остальные тесты
                    # конструктора: клик по карточке в «Курсы и тесты» вёл на страницу
                    # активности с собственной кнопкой «Начать», и до вопроса плеер не
                    # доходил (прогон k8s 14.10).
                    player = ConstructorPlayerPage(student_page)
                    player.open_by_content_id(env.ui_base_url, test["id"])
                    player.start()
                    player.answer_question(_CORRECT_ANSWER)
                    player.finish_test()
                finally:
                    student_context.close()

            with allure.step("3. admin в LRS: Statements, фильтр Agent ID = id слушателя (ретраи до 60 с)"):
                admin_context = browser.new_context(viewport={"width": 1366, "height": 768})
                admin_page = admin_context.new_page()
                try:
                    lrs = LrsAdminPage.login_via_sso(admin_page, env, email, password)
                    clients = lrs.open_stores().open_store("default store")
                    statements_page = LrsStoreStatementsPage(admin_page, store_id=clients.store_id)

                    def _agent_has_statements() -> bool:
                        try:
                            statements_page.open(env)
                            statements_page.filter_by_agent(student["id"])
                        except Exception:
                            return False
                        return statements_page.table.locator("tbody tr").count() > 0

                    found = wait_until(_agent_has_statements, timeout=60, interval=5)
                    assert found, (
                        f"За 60 с в Statements не появились записи для Agent ID={student['id']} — "
                        "LRS периодически теряет postgres/redis (Sentry), см. docs/lrs/lrs_recon.md"
                    )

                    rows = statements_page.table.locator("tbody tr")
                    verbs = {
                        rows.nth(i).locator("td").nth(1).inner_text().strip().lower()
                        for i in range(rows.count())
                    }
                    assert verbs & {"launched", "answered", "passed", "failed"}, verbs

                    with allure.step("4. Предпросмотр statement — homePage пользователя заполнен"):
                        statements_page.open_preview(0)
                        expect(
                            admin_page.get_by_text(f"{env.ui_base_url.rstrip('/')}/accounts/userid", exact=False)
                        ).to_be_visible(timeout=settings.UI_TIMEOUT)

                    with allure.step("5. Вкладка Agents — появился агент с account_name = id слушателя"):
                        agents_page = LrsStoreAgentsPage(admin_page, store_id=clients.store_id)
                        agents_page.open(env)
                        expect(
                            agents_page.table.locator(f"tbody tr:has-text('{student['id']}')")
                        ).to_have_count(1)
                finally:
                    admin_context.close()
        finally:
            AssignmentsEndpoint(api_client).detach_from_individual([test["id"]], [student["id"]])
