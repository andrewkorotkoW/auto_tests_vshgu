"""Разведка TC-E2E-039, раунд 4, develop, 15.10.2026: владелец — "надо пройти активити,
например тест на 1 вопрос, и тогда слушатель получит сертификат". Тест (не опрос — есть
правильный/неправильный ответ) на 1 вопрос, в потоке (program_stream-сертификат на поток),
реально пройден через UI (не change_state). Запуск:
    .venv/bin/python -m pytest scripts/_recon_cert_stream_real_pass.py --env develop -s -v
"""
import os
import pytest
from playwright.sync_api import expect
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import generate_question_payload, generate_certificate_template_payload
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

D = "/private/tmp/claude-502/-Users-andreykorotkow-PycharmProjects-cyber-office/400bc1a1-fbe6-461e-abb3-20a741890d2d/scratchpad/cert_stream_real_pass_recon"


@pytest.mark.api
def test_cert_stream_real_pass(page, env, api_client, created_user, tests_endpoint, assignments_endpoint,
                                 created_program, created_stream, created_module, certificates_endpoint):
    os.makedirs(D, exist_ok=True)

    program = created_program(name="QA_recon_CertRealPass")
    stream = created_stream(program_id=program["id"])
    module = created_module(program_id=program["id"], stream_id=stream["id"])

    tincan_ep = TincanEndpoint(api_client)
    cover_uuid = tincan_ep.upload_cover()
    from api.helpers.data_generator import generate_test_payload
    # completion_percent=0 — порог прохождения 0%, чтобы не зависеть от того, правильно ли
    # отвечено на дефолтный вопрос-заглушку, который бэкенд сам добавляет к новому тесту
    # (наш вопрос с "Правильный ответ"/"Неправильный ответ" — второй, не первый).
    test_data = tests_endpoint.create(generate_test_payload(cover_uuid=cover_uuid, completion_percent=0))
    test_id = test_data["id"]
    q = generate_question_payload(order=1, text="Recon: сколько будет 2+2?", question_type="single")
    tests_endpoint.create_question(test_id, q)
    assignments_endpoint.assign_content_to_module(program["id"], stream["id"], module["id"], [test_id])
    print(f"TEST_ID {test_id} NAME {test_data.get('name')} PROGRAM {program['id']} STREAM {stream['id']}")

    file_id = tincan_ep.upload_certificate_file()
    template = certificates_endpoint.create_template(
        generate_certificate_template_payload(template_type="program_stream", file_id=file_id)
    )
    print("TEMPLATE_ID", template["id"])
    assign_result = certificates_endpoint.assign_template(template["id"], [stream["attributes"]["content_id"]])
    print("ASSIGN_TEMPLATE_RESULT", assign_result)

    user = created_user()
    assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

    try:
        LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
        page.wait_for_timeout(1000)
        sidebar = UserSidebarPage(page)

        program_element = page.locator(f"text={program['name']}").first
        expect(program_element).to_be_visible(timeout=15000)
        program_element.click(force=True)
        sidebar.pass_onboarding()
        page.screenshot(path=f"{D}/01_program_opened.png")

        tests_tab = page.locator("text=Курсы и тесты").first
        expect(tests_tab).to_be_visible(timeout=15000)
        tests_tab.click(force=True)

        test_display_name = test_data.get("name_client") or test_data["name"]
        test_card = page.locator(f"text={test_display_name}").first
        found = False
        for attempt in range(4):
            try:
                expect(test_card).to_be_visible(timeout=10000)
                found = True
                break
            except AssertionError:
                print(f"Тест не найден (попытка {attempt + 1}/4), reload+retry")
                page.wait_for_timeout(5000)
                page.reload()
                sidebar.dismiss_popups()
                page.locator("text=Курсы и тесты").first.click(force=True)
        page.screenshot(path=f"{D}/02_tests_tab.png")
        print("TEST_FOUND_ON_TAB", found)
        if not found:
            return

        test_card.click(force=True)
        page.screenshot(path=f"{D}/03_test_card_opened.png")

        page.wait_for_selector("button.v-btn:has(span:has-text('Начать'))", timeout=15000)
        with page.context.expect_page(timeout=15000) as new_page_info:
            page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button.v-btn');
                    for (const btn of buttons) {
                        if (btn.textContent.includes('Начать')) { btn.click(); break; }
                    }
                }
            """)
        test_page = new_page_info.value
        test_page.wait_for_load_state("domcontentloaded")
        print("PLAYER_URL", test_page.url)

        test_page.wait_for_timeout(8000)
        test_page.screenshot(path=f"{D}/03b_player_initial.png")
        print("PLAYER_INITIAL_BODY", test_page.locator("body").inner_text()[:500].replace("\n", " | "))

        intro_start = test_page.locator("button:has-text('Начать')").first
        if intro_start.count() and intro_start.is_visible(timeout=15000):
            intro_start.click(timeout=10000)
            expect(intro_start).to_be_hidden(timeout=15000)
            test_page.wait_for_timeout(1500)
            test_page.screenshot(path=f"{D}/03c_after_intro_start.png")
            print("PLAYER_AFTER_INTRO_BODY", test_page.locator("body").inner_text()[:500].replace("\n", " | "))

        # Тест оказался на 2 вопроса (бэкенд сам добавляет вопрос-заглушку к новому тесту,
        # наш — второй) — отвечаем в цикле; на нашем вопросе явно берём "Правильный ответ",
        # на заглушке корректного варианта нет — берём первый попавшийся (порог прохождения
        # 0%, см. completion_percent=0 выше, так что это не влияет на итог).
        for i in range(6):
            all_radios = test_page.locator(".v-selection-control")
            n = all_radios.count()
            if n == 0:
                print(f"Больше нет радиобаттонов на итерации {i} — вопросы кончились")
                break
            # :has-text() на .v-selection-control может матчить общий контейнер группы, а не
            # конкретную опцию — ищем ТОЧНО тот элемент, чей собственный текст содержит
            # "Правильный ответ", перебором, а не .first после фильтра.
            radio = None
            for idx in range(n):
                candidate = all_radios.nth(idx)
                if "Правильный ответ" in candidate.inner_text():
                    radio = candidate
                    break
            if radio is None:
                radio = all_radios.first
            if not radio.is_visible(timeout=3000):
                print(f"Радио не видно на итерации {i} — вопросы кончились")
                break
            radio.click(timeout=5000)
            test_page.screenshot(path=f"{D}/04_answer_selected_{i}.png")
            answer_btn = test_page.locator("button:has-text('Ответить')").first
            if answer_btn.count() and answer_btn.is_visible(timeout=2000):
                answer_btn.click(timeout=5000)
            test_page.wait_for_timeout(1500)
            next_btn = test_page.locator(
                "button:has-text('Следующий вопрос'), button:has-text('Далее'), "
                "button:has-text('Завершить'), button:has-text('Закончить')"
            ).first
            if next_btn.count() and next_btn.is_visible(timeout=3000):
                next_btn.click(timeout=5000)
            test_page.wait_for_timeout(1500)
        test_page.screenshot(path=f"{D}/05_final.png")
        print("FINAL_PLAYER_BODY", test_page.locator("body").inner_text()[:500].replace("\n", " | "))

        # Экран "Успешное прохождение" — отдельная кнопка «Завершить», которая, похоже, и
        # фиксирует результат на бэкенде (без неё предыдущий раунд не дал сертификата).
        finish_result_btn = test_page.locator("button:has-text('Завершить')").first
        if finish_result_btn.count() and finish_result_btn.is_visible(timeout=5000):
            finish_result_btn.click(timeout=5000)
            test_page.wait_for_timeout(2000)
            test_page.screenshot(path=f"{D}/05b_after_finish_click.png")
            print("AFTER_FINISH_CLICK_BODY", test_page.locator("body").inner_text()[:300].replace("\n", " | "))

        # Статистика на develop уже показала себя лагающей (другой раунд разведки) — проверяем
        # несколько раз с нарастающим ожиданием вместо одной попытки.
        for wait_s in (20, 30, 40):
            page.wait_for_timeout(wait_s * 1000)
            page.goto(f"{env.ui_base_url}/portal-notifications", wait_until="load")
            page.wait_for_timeout(1500)
            sidebar.dismiss_popups()
            notif_body = page.locator("body").inner_text()
            has_cert = "сертификат" in notif_body.lower()
            print(f"NOTIFICATIONS_HAS_CERT_WORD (+{wait_s}s)", has_cert)
            if has_cert:
                page.screenshot(path=f"{D}/06_notifications.png", full_page=True)
                print("NOTIFICATIONS_BODY", notif_body[:600].replace("\n", " | "))
                break

        page.goto(f"{env.ui_base_url}/profile/{user['id']}", wait_until="load")
        page.wait_for_timeout(2000)
        sidebar.dismiss_popups()
        cert_tab = page.locator("text=Мои сертификаты").first
        cert_tab.click(force=True)
        page.wait_for_timeout(2500)
        page.screenshot(path=f"{D}/07_cert_tab.png", full_page=True)
        print("CERT_TAB_BODY", page.locator("body").inner_text()[:800].replace("\n", " | "))
        print("DONE")
    finally:
        tests_endpoint.delete(test_id)
        certificates_endpoint.delete_templates([template["id"]])
        logger.info("Очистка: тест и шаблон сертификата удалены")
