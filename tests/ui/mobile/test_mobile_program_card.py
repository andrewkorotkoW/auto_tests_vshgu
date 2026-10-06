"""Мобильная вёрстка (Pixel 7): слушатель открывает карточку программы после
прохождения активити — проверяется мобильная вёрстка модуля (три карточки-аккордеона
«Расписание»/«Курсы и тесты»/«Игровая сессия» вместо вкладок в одну строку на desktop,
см. docs/mobile/layout_facts.md п.4).

Данные — те же API-фикстуры, что и в desktop UI-тестах программы/теста
(assigned_user, created_module, tests_endpoint, assignments_endpoint — см.
tests/ui/tests/stream/test_user_test_stream_flow.py), навигация по экрану —
существующие методы PracticalTaskPage (open_programs_list/open_program/
open_courses_and_tests_tab), без новых page objects.
"""
import allure
import pytest
from playwright.sync_api import expect

from api.helpers.data_generator import generate_test_payload, generate_question_payload
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.practical_task_page import PracticalTaskPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Мобильная вёрстка")
@allure.story("Карточка программы после завершения активити")
class TestMobileProgramCard:

    @allure.title("Мобильный (Pixel 7): карточка программы — модуль показывает карточки-аккордеоны")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.ui
    @pytest.mark.mobile
    def test_mobile_program_card(
        self, page, env, api_client, assigned_user, created_module, tincan_endpoint,
        tests_endpoint, assignments_endpoint, is_mobile,
    ):
        assert is_mobile, "Тест должен запускаться с --mobile/MOBILE=1 — иначе он не проверяет мобильную вёрстку"
        allure.dynamic.parameter("device", "Pixel 7")

        with allure.step("1. Подготовить поток, слушателя, модуль и тест (1 вопрос) через API"):
            assigned = assigned_user()
            user, stream = assigned["user"], assigned["stream"]
            prepare_user_for_tests_via_api(env, user["email"], user["password"])
            module = created_module(program_id=stream["program_id"], stream_id=stream["id"])
            program_name = api_client.get(f"/programs/{stream['program_id']}").json()["data"]["attributes"]["name"]

            cover_uuid = tincan_endpoint.upload_cover()
            test_data = tests_endpoint.create(generate_test_payload(cover_uuid=cover_uuid))
            test_id = test_data["id"]
            question = generate_question_payload(order=1, question_type="single")
            tests_endpoint.create_question(test_id, question)

            assigned_ok = assignments_endpoint.assign_content_to_module(
                stream["program_id"], stream["id"], module["id"], [test_id]
            )
            assert assigned_ok, "Не удалось назначить тест в модуль"

        with allure.step(f"2. Войти слушателем '{user['email']}' и пройти тест"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False)
            UserSidebarPage(page).dismiss_popups()

            player = ConstructorPlayerPage(page)
            player.open_by_content_id(env.ui_base_url, test_id)
            player.start()
            page.get_by_text(question["text"], exact=True).wait_for(state="visible", timeout=30000)
            page.get_by_text("Правильный ответ", exact=True).wait_for(state="visible", timeout=15000)
            player.answer_question("Правильный ответ")
            player.finish_test()
            expect(page.get_by_text("Ваш результат:", exact=False)).to_be_visible(timeout=30000)
            player.finish_result_screen()

        with allure.step(f"3. Открыть карточку программы '{program_name}'"):
            task_page = PracticalTaskPage(page)
            task_page.open_programs_list(env.ui_base_url)
            task_page.open_program(program_name)

        with allure.step("4. Модуль показывает карточки-аккордеоны «Расписание»/«Курсы и тесты»/«Игровая сессия»"):
            for label in ("Расписание", "Курсы и тесты", "Игровая сессия"):
                card = page.locator(f"xpath=//span[normalize-space()='{label}']").first
                expect(card).to_be_visible(timeout=15000)

        with allure.step("5. Скриншот карточки программы (вёрстка Pixel 7)"):
            page.screenshot(path="allure-results/mobile_program_card.png")
            allure.attach.file(
                "allure-results/mobile_program_card.png", "Карточка программы (моб.)", allure.attachment_type.PNG
            )
