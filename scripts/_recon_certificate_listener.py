"""Разведка TC-E2E-039 (сертификат слушателя программы, слушательская часть — кабинет,
скачивание), develop, 15.10.2026, раунд 2 (с подсказками владельца: сертификат приходит в
уведомлениях и во вкладке «Сертификаты» профиля; предыдущий раунд не дождался пройдено —
увеличен таймаут дашборда до 60с, как в проверенном тесте). Запуск:
    .venv/bin/python -m pytest scripts/_recon_certificate_listener.py --env develop -s -v
"""
import os
import pytest
from api.endpoints.assignments import CONTENT_STATE_PASSED
from api.helpers.data_generator import generate_certificate_template_payload
from ui.pages.login_page import LoginPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

D = "/private/tmp/claude-502/-Users-andreykorotkow-PycharmProjects-cyber-office/400bc1a1-fbe6-461e-abb3-20a741890d2d/scratchpad/cert_listener_recon"


@pytest.mark.api
def test_certificate_listener_recon(page, env, api_client, created_user, created_program, created_stream,
                                      created_module, created_tincan, tincan_endpoint, modules_endpoint,
                                      assignments_endpoint, certificates_endpoint, dashboards_endpoint):
    os.makedirs(D, exist_ok=True)

    program = created_program(name="QA_recon_Cert2")
    stream = created_stream(program_id=program["id"])
    module = created_module(program_id=program["id"], stream_id=stream["id"])

    cover = tincan_endpoint.upload_cover()
    archive = tincan_endpoint.upload_archive()
    course = created_tincan(archive_uuid=archive, cover_uuid=cover)
    course_id = course["id"]
    tincan_endpoint.assign_to_module(program["id"], stream["id"], module["id"], [course_id])
    stream_content_id = modules_endpoint.find_stream_content_id(program["id"], stream["id"], module["id"], course_id)
    print("STREAM_CONTENT_ID (course)", stream_content_id, "STREAM_OWN_CONTENT_ID", stream["attributes"].get("content_id"))

    file_id = tincan_endpoint.upload_certificate_file()
    template = certificates_endpoint.create_template(
        generate_certificate_template_payload(template_type="program_stream", file_id=file_id)
    )
    print("TEMPLATE_ID", template["id"])
    assign_result = certificates_endpoint.assign_template(template["id"], [stream["attributes"]["content_id"]])
    print("ASSIGN_TEMPLATE_RESULT", assign_result)

    user = created_user()
    assignments_endpoint.assign(program["id"], stream["id"], [user["id"]])

    stream_assignments = assignments_endpoint.list_for_stream(program["id"], stream["id"], [stream_content_id])
    assignment_id = next(int(i["assignment_id"]) for i in stream_assignments if int(i["user_id"]) == user["id"])
    print("ASSIGNMENT_ID", assignment_id)
    assignments_endpoint.change_state(
        user_id=user["id"], assignment_id=assignment_id, stream_content_id=stream_content_id,
        state=CONTENT_STATE_PASSED,
    )
    print("CHANGE_STATE_DONE")

    # Таймаут 60с — тот же, что в проверенном test_status_passed_updates_after_change_state
    # (предыдущий раунд ждал только 30с и мог не дождаться пропагации).
    try:
        course_row = dashboards_endpoint.wait_for_course_row(
            course["name"], stream["id"], predicate=lambda row: row.get("passed", 0) >= 1, timeout=60,
        )
        print("DASHBOARD_COURSE_ROW", course_row)
        passed_confirmed = course_row.get("passed", 0) >= 1
    except Exception as e:
        print("DASHBOARD_COURSE_ROW_TIMEOUT", str(e)[:200])
        passed_confirmed = False
    print("PASSED_CONFIRMED", passed_confirmed)

    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    page.wait_for_timeout(2000)
    sidebar = UserSidebarPage(page)
    page.screenshot(path=f"{D}/00_home.png")

    # Уведомления — владелец: сертификат приходит в уведомлениях.
    page.goto(f"{env.ui_base_url}/portal-notifications", wait_until="load")
    page.wait_for_timeout(2000)
    sidebar.dismiss_popups()
    page.screenshot(path=f"{D}/01_notifications.png", full_page=True)
    notif_body = page.locator("body").inner_text()
    print("NOTIFICATIONS_HAS_CERT_WORD", "сертификат" in notif_body.lower())
    print("NOTIFICATIONS_BODY_HEAD", notif_body[:500].replace("\n", " | "))

    # «Мой профиль» — сначала разобраться, что это (ссылка/модалка), прежде чем кликать вслепую.
    page.goto(f"{env.ui_base_url}/education", wait_until="load")
    page.wait_for_timeout(1500)
    sidebar.dismiss_popups()
    menu = sidebar.open_user_menu()
    profile_item = menu.locator("a, .v-list-item").filter(has_text="Мой профиль").first
    tag_info = profile_item.evaluate("el => ({tag: el.tagName, href: el.getAttribute('href'), outerHTML: el.outerHTML.slice(0, 300)})")
    print("PROFILE_ITEM_INFO", tag_info)

    profile_item.click(force=True)
    page.wait_for_timeout(2500)
    print("AFTER_PROFILE_CLICK_URL", page.url)
    page.screenshot(path=f"{D}/02_after_profile_click.png", full_page=True)
    body = page.locator("body").inner_text()
    print("AFTER_PROFILE_CLICK_HAS_CERT_WORD", "сертификат" in body.lower())

    # Если «Сертификаты» — таб/пункт где-то на этой странице (модалка или настоящая страница).
    cert_tab = page.locator("text=Сертификат").first
    if cert_tab.count():
        print("CERT_TAB_FOUND_TEXT", cert_tab.count())
        cert_tab.click(force=True)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{D}/03_cert_tab.png", full_page=True)
        print("CERT_TAB_BODY", page.locator("body").inner_text()[:800].replace("\n", " | "))
    else:
        print("CERT_TAB_NOT_FOUND")

    logger.info("Разведка сертификата слушателя (раунд 2) завершена")
    print("DONE")
