"""Разведка TC-E2E-039 (сертификат слушателя программы, слушательская часть — кабинет,
скачивание), develop, 15.10.2026. Одноразовый скрипт, не часть прогона. Запуск:
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

    program = created_program(name="QA_recon_Cert")
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
    import time as _time
    for wait_s in (0, 3, 10):
        if wait_s:
            _time.sleep(wait_s)
        after = assignments_endpoint.list_for_stream(program["id"], stream["id"], [stream_content_id])
        after_row = next(i for i in after if int(i["user_id"]) == user["id"])
        print(f"AFTER_CHANGE_STATE_ROW (+{wait_s}s)", {"state": after_row.get("state"), "status": after_row.get("status")})

    # list_for_stream может отражать другое поле, не то, что меняет change-state — сверяем
    # с проверенным источником (дашборд курса), которым пользуется рабочий тест
    # test_courses_table_progress.py::test_status_passed_updates_after_change_state.
    try:
        course_row = dashboards_endpoint.wait_for_course_row(
            course["name"], stream["id"], predicate=lambda row: row.get("passed", 0) >= 1, timeout=30,
        )
        print("DASHBOARD_COURSE_ROW", course_row)
    except Exception as e:
        print("DASHBOARD_COURSE_ROW_TIMEOUT", str(e)[:200])

    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    page.wait_for_timeout(2000)
    sidebar = UserSidebarPage(page)
    page.screenshot(path=f"{D}/00_home.png")

    items = sidebar.user_menu_items()
    print("USER_MENU_ITEMS", items)
    page.screenshot(path=f"{D}/01_user_menu.png")
    sidebar.close_menu()

    # «Моё обучение» / программа — если программа видна и помечена пройденной
    program_element = page.locator(f"text={program['name']}").first
    if program_element.count():
        page.screenshot(path=f"{D}/02_home_with_program.png")
        print("PROGRAM_VISIBLE_ON_HOME", True)
    else:
        print("PROGRAM_VISIBLE_ON_HOME", False)

    page.goto(f"{env.ui_base_url}/education", wait_until="load")
    page.wait_for_timeout(1500)
    sidebar.dismiss_popups()
    go_to_program = page.locator("text=Перейти к программе").first
    if go_to_program.count():
        go_to_program.click(force=True)
        page.wait_for_timeout(2500)
        sidebar.dismiss_popups()
        page.screenshot(path=f"{D}/04_program_detail.png", full_page=True)
        body = page.locator("body").inner_text()
        print("PROGRAM_DETAIL_URL", page.url)
        print("PROGRAM_DETAIL_HAS_CERT_WORD", "сертификат" in body.lower())
        if "сертификат" in body.lower():
            idx = body.lower().index("сертификат")
            print("PROGRAM_DETAIL_CERT_CONTEXT", body[max(0, idx - 80):idx + 150].replace("\n", " | "))
        print("PROGRAM_DETAIL_BODY_HEAD", body[:600].replace("\n", " | "))
    else:
        print("GO_TO_PROGRAM_BUTTON_NOT_FOUND")

    # «Мой профиль» в выпадающем меню — проверить, модалка или переход
    sidebar.open_user_menu()
    profile_link = page.locator(".v-overlay--active a:has-text('Мой профиль'), .v-overlay--active .v-list-item:has-text('Мой профиль')").first
    if profile_link.count():
        profile_link.click(force=True)
        page.wait_for_timeout(2000)
        page.screenshot(path=f"{D}/05_my_profile.png", full_page=True)
        print("MY_PROFILE_URL", page.url)
        body = page.locator("body").inner_text()
        print("MY_PROFILE_HAS_CERT_WORD", "сертификат" in body.lower())

    for path, tag in [("/profile", "profile"), ("/education", "education")]:
        page.goto(f"{env.ui_base_url}{path}", wait_until="load")
        page.wait_for_timeout(2000)
        sidebar.dismiss_popups()
        page.screenshot(path=f"{D}/03_{tag}.png", full_page=True)
        body = page.locator("body").inner_text()
        has_cert_word = "сертификат" in body.lower()
        print(f"PAGE {path} HAS_CERT_WORD", has_cert_word, "URL", page.url)
        if has_cert_word:
            idx = body.lower().index("сертификат")
            print(f"PAGE {path} CERT_CONTEXT", body[max(0, idx - 80):idx + 120].replace("\n", " | "))

    logger.info("Разведка сертификата слушателя завершена (без очистки — фикстуры удалят данные)")
    print("DONE")
