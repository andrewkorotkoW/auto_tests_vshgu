"""Мобильная вёрстка (Pixel 7): слушатель открывает активити (простейший тест,
3 вопроса) и проходит его до результата.

Данные — те же API-фикстуры, что и в desktop UI-тесте того же экрана
(tests/ui/tests/stream/test_user_test_stream_flow.py): assigned_user (поток +
слушатель) + created_module + tests_endpoint + assignments_endpoint. Открытие теста —
ConstructorPlayerPage.open_by_content_id напрямую по content_id (как в
tests/ui/test_constructor/test_08_*), а не через нижнюю панель/карточку программы —
это сознательно обходит мобильную навигацию (бургер-меню/нижняя панель), которая не
предмет этого экрана (вход→список программ уже покрыт test_mobile_login_my_programs).

Facts: docs/mobile/layout_facts.md п.3 — после клика «Начать» страница вопроса иногда
на долю секунды показывает плейсхолдеры («Заголовок вопроса…», «Выберите ответ..»)
вместо реального текста, поэтому ждём реальный текст вопроса отдельным ожиданием
(page.wait_for_function), а не полагаемся на networkidle/game page object (не трогаем
ConstructorPlayerPage — ждём в теле теста).
"""
import allure
import pytest
from playwright.sync_api import expect

from api.helpers.data_generator import generate_test_payload, generate_question_payload
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.test_constructor_player_page import ConstructorPlayerPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Мобильная вёрстка")
@allure.story("Активити: простейший тест")
class TestMobileActivitySimpleTest:

    @allure.title("Мобильный (Pixel 7): слушатель открывает и проходит простейший тест (3 вопроса)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.mobile
    def test_mobile_activity_simple_test(
        self, page, env, api_client, assigned_user, created_module, tincan_endpoint,
        tests_endpoint, assignments_endpoint, is_mobile,
    ):
        assert is_mobile, "Тест должен запускаться с --mobile/MOBILE=1 — иначе он не проверяет мобильную вёрстку"
        allure.dynamic.parameter("device", "Pixel 7")

        with allure.step("1. Подготовить поток, слушателя, модуль и тест с вопросами через API"):
            assigned = assigned_user()
            user, stream = assigned["user"], assigned["stream"]
            prepare_user_for_tests_via_api(env, user["email"], user["password"])
            module = created_module(program_id=stream["program_id"], stream_id=stream["id"])

            cover_uuid = tincan_endpoint.upload_cover()
            test_data = tests_endpoint.create(generate_test_payload(cover_uuid=cover_uuid))
            test_id = test_data["id"]

            question_texts = []
            for i in range(1, 4):
                q = generate_question_payload(order=i, question_type="single")
                tests_endpoint.create_question(test_id, q)
                question_texts.append(q["text"])

            assigned_ok = assignments_endpoint.assign_content_to_module(
                stream["program_id"], stream["id"], module["id"], [test_id]
            )
            assert assigned_ok, "Не удалось назначить тест в модуль"

        with allure.step(f"2. Войти слушателем '{user['email']}'"):
            LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url, handle_onboarding=False)
            UserSidebarPage(page).dismiss_popups()
            assert "/auth" not in page.url, page.url

        with allure.step("3. Открыть тест напрямую по content_id и начать прохождение"):
            player = ConstructorPlayerPage(page)
            player.open_by_content_id(env.ui_base_url, test_id)
            player.start()

        with allure.step("4. Ответить на все вопросы теста"):
            for question_text in question_texts:
                # Дождаться реального текста вопроса, а не плейсхолдера «Заголовок вопроса…»
                # (см. layout_facts.md п.3) — иначе get_by_text(exact=True) ниже не найдёт элемент.
                page.get_by_text(question_text, exact=True).wait_for(state="visible", timeout=30000)
                page.get_by_text("Правильный ответ", exact=True).wait_for(state="visible", timeout=15000)
                player.answer_question("Правильный ответ")
                next_btn = page.get_by_role("button", name="Следующий вопрос")
                finish_btn = page.get_by_role("button", name="Завершить").first
                expect(next_btn.or_(finish_btn)).to_be_visible(timeout=30000)
                if next_btn.is_visible(timeout=500):
                    next_btn.click()

        with allure.step("5. Завершить тест и увидеть результат"):
            player.finish_test()
            expect(page.get_by_text("Ваш результат:", exact=False)).to_be_visible(timeout=30000)

        with allure.step("6. Скриншот финального экрана (вёрстка Pixel 7)"):
            page.screenshot(path="allure-results/mobile_activity_result.png")
            allure.attach.file(
                "allure-results/mobile_activity_result.png", "Результат теста (моб.)", allure.attachment_type.PNG
            )
