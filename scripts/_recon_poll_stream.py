"""Разведка TC-E2E-038 (опрос в потоке + неавторизованная попытка), develop, 15.10.2026.
Одноразовый скрипт, не часть прогона. Запуск:
    .venv/bin/python -m pytest scripts/_recon_poll_stream.py --env develop -s -v
"""
import os
import pytest
from playwright.sync_api import expect
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from api.endpoints.tincan import TincanEndpoint
from api.helpers.data_generator import generate_poll_payload, generate_question_payload
from utils.logger import logger

D = "/private/tmp/claude-502/-Users-andreykorotkow-PycharmProjects-cyber-office/400bc1a1-fbe6-461e-abb3-20a741890d2d/scratchpad/poll_stream_recon"


@pytest.mark.api
def test_poll_stream_recon(page, env, api_client, created_user, polls_endpoint, assignments_endpoint,
                            created_program, created_stream, created_module):
    os.makedirs(D, exist_ok=True)

    program = created_program(name="QA_recon_PollStream")
    stream = created_stream(program_id=program["id"])
    module = created_module(program_id=program["id"], stream_id=stream["id"])
    user = created_user()
    assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

    tincan_ep = TincanEndpoint(api_client)
    cover_uuid = tincan_ep.upload_cover()
    poll = polls_endpoint.create(generate_poll_payload(cover_uuid=cover_uuid))
    poll_id = poll["id"]
    for i in range(1, 3):
        q = generate_question_payload(order=i, text=f"Recon-вопрос #{i}", question_type="single")
        polls_endpoint.create_question(poll_id, q)
    assignments_endpoint.assign_content_to_module(program["id"], stream["id"], module["id"], [poll_id])
    print(f"POLL_ID {poll_id} NAME {poll.get('name')} PROGRAM {program['id']} STREAM {stream['id']}")

    try:
        LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
        page.wait_for_timeout(1000)
        print("AFTER_LOGIN_URL", page.url)
        page.screenshot(path=f"{D}/00_after_login.png")

        program_element = page.locator(f"text={program['name']}").first
        found_program = False
        for attempt in range(4):
            try:
                expect(program_element).to_be_visible(timeout=10000)
                found_program = True
                break
            except AssertionError:
                print(f"Программа не найдена на главной (попытка {attempt + 1}/4), reload+retry")
                page.wait_for_timeout(5000)
                page.reload()
                UserSidebarPage(page).dismiss_popups()
        print("PROGRAM_FOUND", found_program, "URL", page.url)
        page.screenshot(path=f"{D}/01_home.png")
        if not found_program:
            print("BODY_TEXT", page.locator("body").inner_text()[:500].replace("\n", " | "))
            return

        program_element.click(force=True)
        UserSidebarPage(page).pass_onboarding()
        page.screenshot(path=f"{D}/02_program_opened.png")

        tests_tab = page.locator("text=Курсы и тесты").first
        expect(tests_tab).to_be_visible(timeout=15000)
        tests_tab.click(force=True)

        poll_display_name = poll.get("name_client") or poll["name"]
        poll_card = page.locator(f"text={poll_display_name}").first
        found = False
        for attempt in range(4):
            try:
                expect(poll_card).to_be_visible(timeout=10000)
                found = True
                break
            except AssertionError:
                print(f"Опрос не найден (попытка {attempt + 1}/4), reload+retry")
                page.wait_for_timeout(5000)
                page.reload()
                UserSidebarPage(page).dismiss_popups()
                page.locator("text=Курсы и тесты").first.click(force=True)
        page.screenshot(path=f"{D}/03_tests_tab.png")
        print("POLL_FOUND_ON_TAB", found)
        if not found:
            return

        poll_card.click(force=True)
        page.screenshot(path=f"{D}/04_poll_card_opened.png")

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
        poll_page = new_page_info.value
        poll_page.wait_for_load_state("domcontentloaded")
        player_url = poll_page.url
        print("PLAYER_URL", player_url)
        poll_page.screenshot(path=f"{D}/05_player_opened.png")

        # Неавторизованный доступ: та же ссылка в контексте БЕЗ куки сессии.
        anon_context = page.context.browser.new_context()
        anon_page = anon_context.new_page()
        anon_page.goto(player_url, wait_until="load")
        anon_page.wait_for_timeout(2000)
        print("ANON_URL_AFTER_GOTO", anon_page.url)
        anon_page.screenshot(path=f"{D}/06_anon_access.png")
        body_text = anon_page.locator("body").inner_text()[:400].replace("\n", " | ")
        print("ANON_BODY_TEXT", body_text)
        anon_context.close()
        print("DONE")
    finally:
        polls_endpoint.delete(poll_id)
        logger.info("Очистка: опрос удалён")
