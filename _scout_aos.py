import sys
from playwright.sync_api import sync_playwright

from config.environments import ENVIRONMENTS, get_session
from api.client import ApiClient
from api.endpoints.users import UsersEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.schedule_items import ScheduleItemsEndpoint
from api.endpoints.aos import AosEndpoint
from api.endpoints.assignments import AssignmentsEndpoint
from api.helpers.data_generator import (
    generate_user_payload, generate_program_payload, generate_stream_payload,
    generate_module_payload, generate_schedule_item_payload, generate_aos_payload,
)
from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.user_sidebar_page import UserSidebarPage
from ui.pages.login_page import LoginPage

env = ENVIRONMENTS["develop"]
session = get_session(env)
client = ApiClient(session=session, base_url=env.api_base_url, cookie_name=env.cookie_name)

users_ep = UsersEndpoint(client)
programs_ep = ProgramsEndpoint(client)
streams_ep = StreamsEndpoint(client)
modules_ep = ModulesEndpoint(client)
schedule_ep = ScheduleItemsEndpoint(client)
aos_ep = AosEndpoint(client)
assign_ep = AssignmentsEndpoint(client)

payload = generate_user_payload()
user_data = users_ep.create(payload)
user = {"id": user_data["id"], "email": user_data["attributes"]["email"], "password": payload["data"]["attributes"]["password"]}

program = programs_ep.create(generate_program_payload())
stream = streams_ep.create(program["id"], generate_stream_payload())
module = modules_ep.create(program["id"], stream["id"], generate_module_payload())
item = schedule_ep.create(program["id"], stream["id"], module["id"], generate_schedule_item_payload())
aos = aos_ep.create(generate_aos_payload(schedule_item_ids=[item["id"]]))
aos_ep.activate(program["id"], stream["id"], aos["content_id"])
assign_ep.assign(program["id"], stream["id"], [user["id"]])
prepare_user_for_tests_via_api(env, user["email"], user["password"])

program_name = program["attributes"]["name"]
print("PROGRAM:", program_name, "STREAM:", stream["id"], "MODULE:", module["id"], file=sys.stderr)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    LoginPage(page).login(user["email"], user["password"], base_url=env.ui_base_url)
    UserSidebarPage(page).dismiss_popups()
    page.goto(f"{env.ui_base_url}/education")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    print("BODY /education:", page.locator("body").inner_text()[:2500], file=sys.stderr)
    page.screenshot(path="_scout_aos_01_education.png")

    goto_btn = page.locator("button:has-text('Перейти к программе'), a:has-text('Перейти к программе')").first
    goto_btn.click(timeout=10000, force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    UserSidebarPage(page).dismiss_popups()
    print("URL after goto program:", page.url, file=sys.stderr)
    page.wait_for_timeout(3000)
    print("BODY program page (2nd):", page.locator("body").inner_text()[:2500], file=sys.stderr)
    page.screenshot(path="_scout_aos_02_program.png")

    browser.close()

try:
    assign_ep.detach(program["id"], stream["id"], [user["id"]]) if hasattr(assign_ep, "detach") else None
except Exception:
    pass
try:
    streams_ep.delete(program["id"], stream["id"])
except Exception:
    pass
try:
    programs_ep.mass_delete([program["id"]])
except Exception:
    pass
try:
    users_ep.delete(user["id"])
except Exception:
    pass
