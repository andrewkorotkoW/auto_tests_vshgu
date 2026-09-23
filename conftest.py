import os

import allure
import pytest
from api.client import ApiClient
from api.endpoints.users import UsersEndpoint
from api.endpoints.programs import ProgramsEndpoint
from api.endpoints.streams import StreamsEndpoint
from api.endpoints.modules import ModulesEndpoint
from api.endpoints.schedule_items import ScheduleItemsEndpoint
from api.endpoints.aos import AosEndpoint
from api.endpoints.assignments import AssignmentsEndpoint
from playwright.sync_api import sync_playwright
from api.endpoints.lpd import LpdEndpoint
from api.endpoints.onboarding import OnboardingEndpoint
from api.endpoints.info_banner import InfoBannerEndpoint
from api.endpoints.tincan import TincanEndpoint
from api.endpoints.omt_cas import OmtCasEndpoint
from api.endpoints.alpina import AlpinaEndpoint
from api.endpoints.mif import MifEndpoint
from api.endpoints.tests import TestsEndpoint
from api.endpoints.polls import PollsEndpoint
from api.endpoints.knowledge_base import KnowledgeBaseEndpoint
from api.endpoints.homework import HomeworkEndpoint
from api.endpoints.certificates import CertificatesEndpoint
from api.helpers.data_generator import (
    generate_user_payload,
    generate_program_payload,
    generate_stream_payload,
    generate_module_payload,
    generate_schedule_item_payload,
    generate_lpd_payload,
    generate_aos_payload,
    generate_tincan_payload,
    generate_test_payload,
    generate_test_update_payload

)
from config.settings import settings
from config.environments import ENVIRONMENTS, ensure_prod_allowed, get_session, get_storage_state_path
from utils.logger import logger


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("ENV", "develop"),
        choices=list(ENVIRONMENTS.keys()),
        help="Окружение для запуска тестов: develop, stage или prod",
    )


def pytest_configure(config):
    env_name = config.getoption("--env")
    markexpr = config.getoption("-m") or ""
    try:
        ensure_prod_allowed(env_name, markexpr)
    except RuntimeError as exc:
        raise pytest.UsageError(str(exc))


def pytest_collection_modifyitems(config, items):
    """Пропускает тесты с @pytest.mark.env(name), если запуск идёт не под тем окружением,
    и включает один автоповтор (rerunfailures) только для тестов с маркером ui — они
    подвержены флаки из-за реального браузера, а не из-за ошибок в самом тесте.

    Тесты с маркером tools (юнит-тесты test_data_generation/lib.py и т.п., без сети и
    без --env) по умолчанию деселектятся — они не часть обычных api/ui/smoke прогонов
    по стендам и должны запускаться только явным `-m tools` (или выражением, включающим
    tools, например `-m "tools or api"`), либо явным указанием пути tests/tools в
    аргументах запуска (`pytest tests/tools`) — так же, как обычно гоняют один файл/папку
    в обход остального сьюта."""
    markexpr = config.getoption("-m") or ""
    cli_args = config.invocation_params.args
    tools_requested = "tools" in markexpr or any("tests/tools" in str(arg) for arg in cli_args)
    if not tools_requested:
        keep, deselected = [], []
        for item in items:
            (deselected if item.get_closest_marker("tools") else keep).append(item)
        if deselected:
            items[:] = keep
            config.hook.pytest_deselected(items=deselected)

    run_env = config.getoption("--env")
    for item in items:
        marker = item.get_closest_marker("env")
        if marker is not None and marker.args:
            required_env = marker.args[0]
            if required_env != run_env:
                item.add_marker(pytest.mark.skip(
                    reason=f"тест требует env={required_env}, запуск идёт с env={run_env}"
                ))

        if item.get_closest_marker("ui") is not None:
            item.add_marker(pytest.mark.flaky(reruns=1))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Скриншот Playwright-страницы при падении UI-теста, прикреплённый в allure."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return

    page = item.funcargs.get("page") or item.funcargs.get("admin_page") or item.funcargs.get("user_page")
    if page is None:
        return

    try:
        allure.attach(
            page.screenshot(full_page=True),
            name="failure_screenshot",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception as exc:  # noqa: BLE001 — страница могла уже закрыться к моменту хука
        logger.info(f"Не удалось сделать скриншот при падении: {exc}")


@pytest.fixture(scope="session")
def env(request):
    """Окружение, выбранное флагом --env (по умолчанию develop)."""
    return ENVIRONMENTS[request.config.getoption("--env")]


@pytest.fixture(scope="session")
def env_session(env):
    """Авторизованная requests.Session для выбранного окружения (с кэшем в .cache/)."""
    return get_session(env)


@pytest.fixture(scope="session")
def admin_session(env):
    """Сессия администратора выбранного окружения."""
    return get_session(env, role="admin")


@pytest.fixture(scope="session")
def user_session(env):
    """Сессия обычного пользователя (слушателя) выбранного окружения."""
    return get_session(env, role="user")


@pytest.fixture(scope="function")
def api_client(env, env_session):
    """Клиент API — сессия из фикстуры env (реальный логин или кэш, .env как fallback)."""
    client = ApiClient(session=env_session, base_url=env.api_base_url, cookie_name=env.cookie_name)
    yield client


@pytest.fixture
def users_endpoint(api_client):
    return UsersEndpoint(api_client)


@pytest.fixture
def programs_endpoint(api_client):
    return ProgramsEndpoint(api_client)


@pytest.fixture
def streams_endpoint(api_client):
    return StreamsEndpoint(api_client)


@pytest.fixture
def modules_endpoint(api_client):
    return ModulesEndpoint(api_client)


@pytest.fixture
def schedule_items_endpoint(api_client):
    return ScheduleItemsEndpoint(api_client)


@pytest.fixture
def aos_endpoint(api_client):
    return AosEndpoint(api_client)


@pytest.fixture
def created_user(api_client, users_endpoint):
    user_ids = []

    def _create(**kwargs):
        payload = generate_user_payload(**kwargs)
        user_data = users_endpoint.create(payload)
        user_ids.append(user_data["id"])
        return {
            "id": user_data["id"],
            "email": user_data["attributes"]["email"],
            "name": user_data["attributes"]["name"],
            "surname": user_data["attributes"]["surname"],
            "patronymic": user_data["attributes"]["patronymic"],
            "password": payload["data"]["attributes"]["password"],
            "attributes": user_data["attributes"]
        }

    yield _create

    for user_id in user_ids:
        try:
            users_endpoint.delete(user_id)
        except Exception as e:
            logger.warning(f"Failed to delete user {user_id}: {e}")


@pytest.fixture
def prepared_user(env, created_user):
    """Пользователь, готовый к UI-сценариям слушателя: created_user + согласие на ПД,
    отключение рекламной рассылки и закрытие onboarding-историй через API
    (api.helpers.user_prepare_api.prepare_user_for_tests_via_api) — без этого при
    первом входе в браузере виснет модалка «Пожалуйста, заполните некоторые данные
    о себе», перекрывающая всю страницу."""
    from api.helpers.user_prepare_api import prepare_user_for_tests_via_api

    def _create(**kwargs):
        user = created_user(**kwargs)
        prepare_user_for_tests_via_api(env, user["email"], user["password"])
        return user

    yield _create


@pytest.fixture
def created_program(api_client, programs_endpoint):
    program_ids = []

    def _create(**kwargs):
        payload = generate_program_payload(**kwargs)
        program_data = programs_endpoint.create(payload)
        program_ids.append(program_data["id"])
        return {
            "id": program_data["id"],
            "name": program_data["attributes"]["name"],
            "attributes": program_data["attributes"]
        }

    yield _create

    if program_ids:
        try:
            programs_endpoint.mass_delete(program_ids)
        except Exception as e:
            logger.warning(f"Failed to mass delete programs {program_ids}: {e}")


@pytest.fixture
def created_stream(api_client, streams_endpoint, created_program):
    """Создаёт программу и поток внутри неё. Удаляет после теста."""
    stream_ids = []

    def _create(program_id=None, **kwargs):
        if program_id is None:
            program = created_program()
            program_id = program["id"]

        payload = generate_stream_payload(**kwargs)
        stream_data = streams_endpoint.create(program_id, payload)
        stream_ids.append((program_id, stream_data["id"]))
        return {
            "id": stream_data["id"],
            "program_id": program_id,
            "name": stream_data["attributes"]["name"],
            "attributes": stream_data["attributes"]
        }

    yield _create

    for program_id, stream_id in stream_ids:
        try:
            streams_endpoint.delete(program_id, stream_id)
        except Exception as e:
            logger.warning(f"Failed to delete stream {stream_id}: {e}")


@pytest.fixture
def created_module(api_client, modules_endpoint, created_program, created_stream):
    """Создаёт программу → поток → модуль. Удаляет после теста."""
    module_ids = []

    def _create(program_id=None, stream_id=None, **kwargs):
        if program_id is None:
            program = created_program()
            program_id = program["id"]
        if stream_id is None:
            stream = created_stream(program_id=program_id)
            stream_id = stream["id"]
        payload = generate_module_payload(**kwargs)
        module_data = modules_endpoint.create(program_id, stream_id, payload)
        module_ids.append((program_id, stream_id, module_data["id"]))
        return {
            "id": module_data["id"],
            "program_id": program_id,
            "stream_id": stream_id,
            "name": module_data["attributes"]["name"],
            "attributes": module_data["attributes"]
        }

    yield _create

    for program_id, stream_id, module_id in module_ids:
        try:
            modules_endpoint.delete(program_id, stream_id, module_id)
        except Exception as e:
            logger.warning(f"Failed to delete module {module_id}: {e}")


@pytest.fixture
def created_schedule_item(api_client, schedule_items_endpoint, created_program, created_stream, created_module):
    """Создаёт программу → поток → модуль → элемент расписания. Удаляет после."""
    schedule_ids = []

    def _create(**kwargs):
        program = created_program()
        stream = created_stream(program_id=program["id"])
        module = created_module(program_id=program["id"], stream_id=stream["id"])
        payload = generate_schedule_item_payload(**kwargs)
        item_data = schedule_items_endpoint.create(program["id"], stream["id"], module["id"], payload)
        schedule_ids.append((program["id"], stream["id"], module["id"], item_data["id"]))
        return {
            "id": item_data["id"],
            "program_id": program["id"],
            "stream_id": stream["id"],
            "module_id": module["id"],
            "name": item_data["attributes"]["name"],
            "attributes": item_data["attributes"]
        }

    yield _create

    for program_id, stream_id, module_id, item_id in schedule_ids:
        try:
            schedule_items_endpoint.delete(program_id, stream_id, module_id, item_id)
        except Exception as e:
            logger.warning(f"Failed to delete schedule item {item_id}: {e}")


@pytest.fixture
def created_aos(api_client, aos_endpoint, created_schedule_item):
    """Создаёт schedule item → АОС. Удаляет после теста."""
    aos_ids = []

    def _create(schedule_item_id=None, **kwargs):
        if schedule_item_id is None:
            item = created_schedule_item()
            schedule_item_id = item["id"]
            program_id = item["program_id"]
            stream_id = item["stream_id"]
            # Получаем имя программы через API
            prog_resp = api_client.get(f"/programs/{program_id}")
            program_name = prog_resp.json()["data"]["attributes"]["name"]
        else:
            program_id = None
            stream_id = None
            program_name = "Программа"
        payload = generate_aos_payload(schedule_item_ids=[schedule_item_id], **kwargs)
        data = aos_endpoint.create(payload)
        aos_ids.append(data["content_id"])
        return {
            "id": data["content_id"],
            "name": data["name"],
            "attributes": data,
            "schedule_item_id": schedule_item_id,
            "program_id": program_id,
            "stream_id": stream_id,
            "program_name": program_name
        }

    yield _create

@pytest.fixture
def assignments_endpoint(api_client):
    return AssignmentsEndpoint(api_client)


@pytest.fixture
def assigned_user(api_client, created_user, created_stream, assignments_endpoint):
    """Создаёт пользователя, поток и назначает пользователя в поток."""

    def _create():
        user = created_user()
        stream = created_stream()
        assignments_endpoint.assign(stream["program_id"], stream["id"], [user["id"]])
        return {
            "user": user,
            "stream": stream
        }

    yield _create

@pytest.fixture(scope="session")
def browser():
    """Запуск браузера на всю сессию."""
    # HEADLESS=1 (по умолчанию в Docker, см. Dockerfile) — без окна браузера;
    # локально по умолчанию окно открывается, как и раньше.
    headless = os.getenv("HEADLESS", "0").lower() in ("1", "true", "yes")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    yield page
    context.close()


def _authenticated_page(browser, env, role):
    """Открывает страницу с уже применённым Playwright storage_state, полученным
    из авторизованной requests.Session (см. config/environments.get_storage_state_path) —
    без ручного логина через форму в каждом тесте."""
    storage_state_path = get_storage_state_path(env, role=role)
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        storage_state=str(storage_state_path),
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def admin_page(browser, env):
    """Страница Playwright, уже авторизованная под администратором окружения."""
    yield from _authenticated_page(browser, env, "admin")


@pytest.fixture
def user_page(browser, env):
    """Страница Playwright, уже авторизованная под обычным пользователем (слушателем)."""
    yield from _authenticated_page(browser, env, "user")

@pytest.fixture
def onboarding_endpoint(api_client):
    return OnboardingEndpoint(api_client)

@pytest.fixture
def lpd_endpoint(api_client):
    return LpdEndpoint(api_client)

@pytest.fixture
def created_lpd(api_client, lpd_endpoint):
    """Создаёт LPD. Удаляет после теста."""
    lpd_ids = []

    def _create(**kwargs):
        logger.info(f"created_lpd kwargs: {kwargs}")
        payload = generate_lpd_payload(**kwargs)
        data = lpd_endpoint.create(payload)
        logger.info(f"Data received: {data}")
        if data is None:
            raise ValueError("create returned None")
        lpd_ids.append(data["id"])
        return {
            "id": data["id"],
            "name": data["attributes"]["name"],
            "attributes": data["attributes"]
        }

    yield _create

    for lpd_id in lpd_ids:
        try:
            lpd_endpoint.delete(lpd_id)
        except Exception as e:
            logger.warning(f"Failed to delete LPD {lpd_id}: {e}")

@pytest.fixture
def api_client_global(env, env_session):
    client = ApiClient(session=env_session, base_url=env.global_base_url, cookie_name=env.cookie_name)
    yield client

@pytest.fixture
def info_banner_endpoint(api_client_global):
    return InfoBannerEndpoint(api_client_global)

@pytest.fixture
def tincan_endpoint(api_client):
    return TincanEndpoint(api_client)

@pytest.fixture
def created_tincan(api_client, tincan_endpoint):
    tincan_ids = []

    def _create(**kwargs):
        payload = generate_tincan_payload(**kwargs)
        data = tincan_endpoint.create(payload)
        tincan_ids.append(data["id"])
        return {
            "id": data["id"],
            "name": data["attributes"]["name"],
            "attributes": data["attributes"]
        }

    yield _create

    if tincan_ids:
        try:
            tincan_endpoint.mass_delete(tincan_ids)
        except Exception as e:
            logger.warning(f"Failed to delete Tincan {tincan_ids}: {e}")

@pytest.fixture
def omt_cas_endpoint(api_client):
    return OmtCasEndpoint(api_client)

@pytest.fixture
def external_cas_endpoint(env, env_session):
    import requests
    # Своя сессия (не общий env_session), чтобы не примешивать Authorization/Content-Type
    # в остальные фикстуры, которые переиспользуют ту же (session-scope) сессию логина.
    session = requests.Session()
    session.cookies.update(env_session.cookies)
    session.headers["Authorization"] = env.cas_auth_token  # без Bearer
    session.headers["Accept"] = "application/json"
    session.headers["Content-Type"] = "application/json"

    from api.endpoints.external_cas import ExternalCasEndpoint
    from api.client import ApiClient
    client = ApiClient(session=session, base_url=env.api_base_url)
    return ExternalCasEndpoint(client)

@pytest.fixture
def external_system_client(env, env_session):
    import requests
    from api.client import ApiClient
    # Своя сессия (не общий env_session), чтобы Authorization не примешивался
    # в остальные фикстуры, которые переиспользуют ту же (session-scope) сессию логина.
    session = requests.Session()
    session.cookies.update(env_session.cookies)
    client = ApiClient(
        session=session,
        auth_token=env.external_system_client_token,
        base_url=env.api_base_url,
    )
    return client

@pytest.fixture
def alpina_endpoint(api_client):
    return AlpinaEndpoint(api_client)


@pytest.fixture
def mif_endpoint(api_client):
    return MifEndpoint(api_client)

@pytest.fixture
def tests_endpoint(api_client):
    from api.endpoints.tests import TestsEndpoint
    return TestsEndpoint(api_client)

@pytest.fixture
def created_test(api_client, tests_endpoint):
    """Создаёт тест (type=test). Удаляет после теста."""
    test_ids = []

    def _create(**kwargs):
        from api.helpers.data_generator import generate_test_payload
        payload = generate_test_payload(**kwargs)
        data = tests_endpoint.create(payload)
        test_ids.append(data["id"])
        return {
            "id": data["id"],
            "name": data["name"],
            "attributes": data
        }

    yield _create

    for test_id in test_ids:
        try:
            tests_endpoint.delete(test_id)
        except Exception as e:
            logger.warning(f"Failed to delete test {test_id}: {e}")

@pytest.fixture
def polls_endpoint(api_client):
    return PollsEndpoint(api_client)

@pytest.fixture
def created_poll(api_client, polls_endpoint):
    """Создаёт опрос (type=poll). НЕ удаляет после теста."""
    def _create(**kwargs):
        from api.helpers.data_generator import generate_poll_payload
        payload = generate_poll_payload(**kwargs)
        data = polls_endpoint.create(payload)
        return {
            "id": data["id"],
            "name": data["name"],
            "name_client": data.get("name_client", data["name"]),
            "attributes": data
        }

    yield _create

@pytest.fixture
def knowledge_base_endpoint(api_client):
    return KnowledgeBaseEndpoint(api_client)

@pytest.fixture
def created_material(api_client, knowledge_base_endpoint):
    """Создаёт материал в базе знаний. НЕ удаляет после теста."""
    def _create(**kwargs):
        from api.helpers.data_generator import generate_material_payload
        payload = generate_material_payload(**kwargs)
        data = knowledge_base_endpoint.create_material(payload)
        return {
            "id": data["id"],
            "name": data.get("name"),
            "attributes": data
        }
    yield _create

@pytest.fixture
def created_material(api_client, knowledge_base_endpoint):
    """Создаёт материал в базе знаний и удаляет после теста."""
    material_ids = []

    def _create(**kwargs):
        from api.helpers.data_generator import generate_material_payload
        payload = generate_material_payload(**kwargs)
        data = knowledge_base_endpoint.create_material(payload)
        material_ids.append(data["id"])
        return {
            "id": data["id"],
            "name": data.get("name"),
            "attributes": data
        }

    yield _create

    # Автоочистка
    if material_ids:
        try:
            knowledge_base_endpoint.delete_materials(material_ids)
        except Exception as e:
            logger.warning(f"Failed to delete materials {material_ids}: {e}")

@pytest.fixture
def homework_endpoint(api_client):
    return HomeworkEndpoint(api_client)

@pytest.fixture
def created_homework(api_client, homework_endpoint):
    """Создаёт практическое задание (homework). НЕ удаляет после теста."""
    def _create(**kwargs):
        from api.helpers.data_generator import generate_homework_payload
        payload = generate_homework_payload(**kwargs)
        data = homework_endpoint.create(payload)
        return {
            "id": data["id"],
            "name": data["attributes"]["name"],
            "name_client": data["attributes"]["name_client"],
            "attributes": data["attributes"]
        }
    yield _create

from api.endpoints.homework_ten_point import HomeworkTenPointEndpoint

@pytest.fixture
def homework_ten_point_endpoint(api_client):
    return HomeworkTenPointEndpoint(api_client)

@pytest.fixture
def created_homework_ten_point(api_client, homework_ten_point_endpoint):
    """Создаёт практическое задание (10‑балльное). НЕ удаляет после теста."""
    def _create(**kwargs):
        from api.helpers.data_generator import generate_homework_ten_point_payload
        payload = generate_homework_ten_point_payload(**kwargs)
        data = homework_ten_point_endpoint.create(payload)
        return {
            "id": data["id"],
            "name": data["attributes"]["name"],
            "name_client": data["attributes"]["name_client"],
            "attributes": data["attributes"]
        }
    yield _create

from api.endpoints.homework_pass_fail import HomeworkPassFailEndpoint

@pytest.fixture
def homework_pass_fail_endpoint(api_client):
    return HomeworkPassFailEndpoint(api_client)

@pytest.fixture
def created_homework_pass_fail(api_client, homework_pass_fail_endpoint):
    """Создаёт практическое задание (зачёт/незачёт). НЕ удаляет после теста."""
    def _create(**kwargs):
        from api.helpers.data_generator import generate_homework_pass_fail_payload
        payload = generate_homework_pass_fail_payload(**kwargs)
        data = homework_pass_fail_endpoint.create(payload)
        return {
            "id": data["id"],
            "name": data["attributes"]["name"],
            "name_client": data["attributes"]["name_client"],
            "attributes": data["attributes"]
        }
    yield _create

@pytest.fixture
def certificates_endpoint(api_client):
    return CertificatesEndpoint(api_client)

@pytest.fixture
def created_template(api_client, certificates_endpoint):
    """Создаёт шаблон сертификата и удаляет после теста."""
    template_ids = []

    def _create(**kwargs):
        from api.helpers.data_generator import generate_certificate_template_payload
        payload = generate_certificate_template_payload(**kwargs)
        data = certificates_endpoint.create_template(payload)
        template_ids.append(data["id"])
        return data

    yield _create

    if template_ids:
        try:
            certificates_endpoint.delete_templates(template_ids)
        except Exception as e:
            logger.warning(f"Failed to delete templates {template_ids}: {e}")

@pytest.fixture
def stage_api_client():
    """Клиент API для Stage окружения (сессия из реального логина или кэша, .env как fallback)."""
    stage_env = ENVIRONMENTS["stage"]
    session = get_session(stage_env)
    client = ApiClient(session=session, base_url=stage_env.api_base_url, cookie_name=stage_env.cookie_name)
    yield client




# ---------- Интеграция БУК (входящий REST /external/buk/users) ----------

@pytest.fixture
def external_buk_endpoint(env, env_session):
    """Клиент входящего REST БУК: JWT в Authorization без Bearer (<ENV>_BUK_TOKEN).

    Своя requests.Session, как у external_cas_endpoint, чтобы не трогать общую сессию логина.
    Все buk_user_id, которые прошли через post_user/put_user, снимаются DELETE в teardown —
    иначе email тестовых пользователей остаётся связанным и ломает повторные прогоны.
    """
    if not env.buk_token:
        pytest.skip(f"Не задан {env.name.upper()}_BUK_TOKEN в .env — тесты БУК пропущены")
    import requests
    from api.client import ApiClient
    from api.endpoints.external_buk import ExternalBukEndpoint

    session = requests.Session()
    session.cookies.update(env_session.cookies)
    session.headers["Authorization"] = env.buk_token
    client = ApiClient(session=session, base_url=env.api_base_url)
    endpoint = ExternalBukEndpoint(client)

    sent = []
    orig_post, orig_put = endpoint.post_users, endpoint.put_users

    def _track(users):
        sent.extend(u.get("buk_user_id") for u in users if u.get("buk_user_id"))

    endpoint.post_users = lambda users: (_track(users), orig_post(users))[1]
    endpoint.put_users = lambda users: (_track(users), orig_put(users))[1]

    yield endpoint

    ids = list(dict.fromkeys(sent))
    if ids:
        try:
            endpoint.delete_users(ids)
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"BUK cleanup failed for {ids}: {exc}")
