"""Фикстуры для tests/ui/helpdesk/admin — UI-тесты админки хелпдеска (Laravel Backpack,
отдельный домен от остальной Vue-админки портала, см. ui/pages/helpdesk_base_page.py).

Страница — `admin_page` из корневого conftest.py (storage_state уже авторизован на
поддомене `.d2.devspark.ru`, тот же cookie работает и на helpdesk-develop без отдельного
логина, см. ui/pages/helpdesk_base_page.py). `helpdesk_endpoint` в этом пакете используется
для read-only подготовки данных (поиск заявителя с реально назначенным потоком обучения
для APPLICANTS-008, список пользователей для existing_helpdesk_user_id) И для создания
тестовых заявителей (add_applicant — подтверждено живым прогоном, что для заявителей
сырая POST-эмуляция формы работает корректно, в отличие от групп/шаблонов ниже).

Создание/удаление групп и шаблонов через HelpdeskEndpoint здесь НЕ используется: сырая
POST-эмуляция формы в api/endpoints/helpdesk.py не отправляет часть скрытых полей
настоящей формы (`_form_id`/`admins_collection`/корректный `_http_referrer` у групп,
`type=user` у шаблонов) и либо откатывается валидацией (группы — созданная запись не
сохраняется, несмотря на status < 400), либо падает 500 (шаблоны — NOT NULL на
`mail_templates.type`, проверено живым запросом на develop). Поэтому тестовые
группы/шаблоны создаются и удаляются целиком через сами page-объекты
(HelpdeskGroupsPage.create_group/delete_group, HelpdeskTemplatesPage.create_template/
delete_template)."""
import re

import pytest

from api.client import ApiClient
from api.endpoints.helpdesk import HelpdeskEndpoint
from ui.pages.helpdesk_users_page import HelpdeskUsersPage

HELPDESK_BASE_URL_DEFAULT = "https://helpdesk-develop.d2.devspark.ru"

def _helpdesk_base_url(env) -> str:
    """Хост хелпдеска для текущего стенда: явный HELPDESK_URL, иначе portal-<stand> → helpdesk-<stand>
    (develop → helpdesk-develop.d2.devspark.ru, k8s → helpdesk-k8s-release.v2.gosedu.ru); сессионная
    кука общая для поддомена, отдельный логин не нужен."""
    import os
    explicit = os.getenv("HELPDESK_URL")
    if explicit:
        return explicit.rstrip("/")
    ui = env.ui_base_url.rstrip("/")
    if "://portal-" in ui:
        return ui.replace("://portal-", "://helpdesk-")
    if "://portal." in ui:
        return ui.replace("://portal.", "://helpdesk.")
    return HELPDESK_BASE_URL_DEFAULT


_STREAM_SELECT_RE = re.compile(r"Программы и потоки.*?</select>", re.S)
_STREAM_OPTION_RE = re.compile(r'<option[^>]*value="(\d+)"[^>]*>')
_SHOW_ID_RE = re.compile(r"/admin/identity/(\d+)/show")


@pytest.fixture
def helpdesk_ui_base_url(env) -> str:
    return _helpdesk_base_url(env)


@pytest.fixture
def helpdesk_endpoint(env, admin_session):
    """Только read-only использование в этом пакете (см. докстринг модуля)."""
    client = ApiClient(session=admin_session, base_url=_helpdesk_base_url(env), cookie_name=env.cookie_name)
    return HelpdeskEndpoint(client)


_USER_SHOW_ID_RE = re.compile(r"/admin/user/(\d+)/show")


@pytest.fixture
def existing_helpdesk_user_id(helpdesk_endpoint) -> int:
    """ID первого пользователя из уже существующего списка /admin/user (read-only,
    helpdesk_endpoint.search_user) — нужен для TC-HELPDESK_USERS-002/003/004: свежесозданный
    через портальный API пользователь (fixture created_user из корневого conftest.py) в
    этом списке не появляется вовсе (см. блокер в docstring test_users.py::test_assign_role),
    поэтому карточку/настройки таблицы тикетов проверяем на уже существующем пользователе —
    его ФИО/email/роли не меняем, только настройки отображения таблицы тикетов, и то с
    гарантированным восстановлением (см. restore_ticket_table_columns)."""
    data = helpdesk_endpoint.search_user("")
    rows = data.get("data", [])
    assert rows, "В списке /admin/user нет ни одного пользователя — нечего проверять"
    row_html = "".join(rows[0])
    match = _USER_SHOW_ID_RE.search(row_html)
    assert match, f"Не удалось извлечь ID пользователя из первой строки списка: {row_html[:200]}"
    return int(match.group(1))


@pytest.fixture
def restore_ticket_table_columns(admin_page, helpdesk_ui_base_url):
    """Гарантирует восстановление исходного списка колонок таблицы тикетов пользователя
    даже при падении теста: тест должен сразу после чтения текущих настроек (до любых
    изменений) вызвать register(user_id, original_columns); восстановление выполняется в
    teardown фикстуры (после yield), который pytest выполняет независимо от исхода теста —
    в отличие от кода после assert в теле теста, упавший assert это не пропустит."""
    page = HelpdeskUsersPage(admin_page)
    state = {}

    def _register(user_id: int, original_columns: list) -> None:
        state["user_id"] = user_id
        state["original_columns"] = original_columns

    yield _register

    if state:
        page.open_edit_form(helpdesk_ui_base_url, state["user_id"])
        page.set_ticket_table_columns(state["original_columns"])


@pytest.fixture
def applicant_with_education_stream(helpdesk_endpoint):
    """Ищет (только чтение, без мутаций) среди заявителей того, у кого реально назначен
    поток обучения — нужен для APPLICANTS-008/test_navigate_to_user_education_tab, такие
    данные не создаются автоматизацией (учебный домен вне скоупа миссии, см.
    docs/test_cases/helpdesk/applicants.md APPLICANTS-006/007). Возвращает ID первого
    подходящего заявителя или None, если на стенде такого не нашлось (в этом случае тест,
    использующий фикстуру, должен сам решить xfail).

    Перебирает ВСЕХ заявителей постранично (не только первую страницу, как было раньше):
    подходящих реально мало — подтверждено живым прогоном, на develop только 2 из 176
    заявителей назначены на поток, и ни один не попадает в первые 25 строк дефолтной
    сортировки списка, из-за чего однострадничный поиск систематически не находил
    существующих данных и фикстура всегда возвращала None. `/admin/identity/search` не
    принимает `length` больше 50 (большие значения, включая -1/«все», отвечают 400 "Unknown
    page length") — поэтому идём страницами по 50 через `search_applicant()`
    (HelpdeskEndpoint.search_applicant не параметризует start/length — они оба фиксированы
    на 0/25 — поэтому страницы запрашиваются тем же HTTP-контрактом напрямую)."""
    client = helpdesk_endpoint.client
    page_size = 50
    start = 0
    while True:
        resp = client.session.post(
            f"{client.base_url}{helpdesk_endpoint.IDENTITY_PATH}/search",
            data={"draw": 1, "start": start, "length": page_size, "search[value]": "", "search[regex]": "false"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=client.timeout,
        )
        data = resp.json()
        rows = data.get("data", [])
        if not rows:
            return None
        for row in rows:
            row_html = "".join(row)
            match = _SHOW_ID_RE.search(row_html)
            if not match:
                continue
            applicant_id = int(match.group(1))
            html = helpdesk_endpoint.get_applicant(applicant_id)
            if "Управление обучением" not in html:
                continue
            select_match = _STREAM_SELECT_RE.search(html)
            if select_match and _STREAM_OPTION_RE.search(select_match.group(0)):
                return applicant_id
        start += page_size
        if start >= data.get("recordsTotal", 0):
            return None
