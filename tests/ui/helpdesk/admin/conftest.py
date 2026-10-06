"""Фикстуры для tests/ui/helpdesk/admin — UI-тесты админки хелпдеска (Laravel Backpack,
отдельный домен от остальной Vue-админки портала, см. ui/pages/helpdesk_base_page.py).

Страница — `admin_page` из корневого conftest.py (storage_state уже авторизован на
поддомене `.d2.devspark.ru`, тот же cookie работает и на helpdesk-develop без отдельного
логина, см. ui/pages/helpdesk_base_page.py). `helpdesk_endpoint` в этом пакете используется
ТОЛЬКО для read-only подготовки данных (поиск заявителя с реально назначенным потоком
обучения для APPLICANTS-008) — создание/удаление групп и шаблонов через
HelpdeskEndpoint здесь не используется: сырая POST-эмуляция формы в
api/endpoints/helpdesk.py не отправляет часть скрытых полей настоящей формы
(`_form_id`/`admins_collection`/корректный `_http_referrer` у групп, `type=user` у
шаблонов) и либо откатывается валидацией (группы — созданная запись не сохраняется,
несмотря на status < 400), либо падает 500 (шаблоны — NOT NULL на `mail_templates.type`,
проверено живым запросом на develop). Поэтому тестовые группы/шаблоны создаются и
удаляются целиком через сами page-объекты (HelpdeskGroupsPage.create_group/delete_group,
HelpdeskTemplatesPage.create_template/delete_template)."""
import re

import pytest

from api.client import ApiClient
from api.endpoints.helpdesk import HelpdeskEndpoint

HELPDESK_UI_BASE_URL = "https://helpdesk-develop.d2.devspark.ru"

_STREAM_SELECT_RE = re.compile(r"Программы и потоки.*?</select>", re.S)
_STREAM_OPTION_RE = re.compile(r'<option[^>]*value="(\d+)"[^>]*>')
_SHOW_ID_RE = re.compile(r"/admin/identity/(\d+)/show")


@pytest.fixture
def helpdesk_ui_base_url() -> str:
    return HELPDESK_UI_BASE_URL


@pytest.fixture
def helpdesk_endpoint(env, admin_session):
    """Только read-only использование в этом пакете (см. докстринг модуля)."""
    client = ApiClient(session=admin_session, base_url=HELPDESK_UI_BASE_URL, cookie_name=env.cookie_name)
    return HelpdeskEndpoint(client)


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
