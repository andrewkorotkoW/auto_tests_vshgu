import re
from typing import Dict, Optional

import requests

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

_CSRF_META_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)">')
_ROW_ID_RE = re.compile(r"/(\d+)(?:/edit|/show)?[\"']")


class HelpdeskEndpoint:
    """Методы для админки хелпдеска (https://helpdesk-develop.d2.devspark.ru/admin/*).

    В отличие от остальных эндпоинтов портала, хелпдеск — не JSON REST API, а
    сервер-рендерящаяся Laravel Backpack-админка (см. docs/helpdesk_recon.md):
    списки отдают HTML, карточки/формы — тоже HTML, подгрузка строк таблицы —
    отдельный `POST {path}/search` с параметрами jQuery DataTables (draw/start/
    length/search[value]), отвечающий JSON {"data": [[...готовый HTML ячеек...]]}.
    Форма создания/редактирования — classic POST/PUT с CSRF-токеном (`_token`,
    берётся из мета-тега `<meta name="csrf-token">` на странице) и служебными
    скрытыми полями Backpack (`_method`, `_http_referrer`, `_form_id`,
    `_save_action`). Удаление — DELETE на `data-route` иконки-корзины с тем же
    токеном в заголовке `X-CSRF-TOKEN`.

    `client.base_url` должен указывать на корень хелпдеска (например
    `https://helpdesk-develop.d2.devspark.ru`, без `/api/v1` — в отличие от
    клиентов остальных эндпоинтов портала), а `client.session` — быть той же
    авторизованной сессией admin develop (кука общая для домена `.d2.devspark.ru`,
    отдельный логин на хелпдеск не нужен).

    Точные `name`-атрибуты полей форм групп/шаблонов/заявителей разведка
    зафиксировала только как подписи (кроме `users_collection[]` у групп и
    `roles[admin|support|group_admin]` у назначения ролей — эти два подтверждены
    буквально по DOM/сети) — остальные ключи payload собраны по конвенции Laravel
    Backpack CRUD (snake_case от названия колонки). При первом реальном создании
    сущности проверить, что сервер принял форму (редирект/200, а не 422 с
    ошибками валидации по незнакомым полям), и поправить ключи в
    api/helpers/data_generator.py при расхождении.

    Группы — только свои `Автотест_*` с фиктивными IMAP/SMTP: не трогать
    системные группы и их почтовые реквизиты (см. generate_helpdesk_group_payload).
    """

    GROUP_PATH = "/admin/group"
    TEMPLATE_PATH = "/admin/mail-template"
    USER_PATH = "/admin/user"
    IDENTITY_PATH = "/admin/identity"
    TICKET_PATH = "/admin/ticket"

    def __init__(self, client: ApiClient):
        self.client = client

    # ---- внутренняя Backpack-механика (CSRF, форма, DataTables-поиск) ----

    def _url(self, path: str) -> str:
        return f"{self.client.base_url}{path}"

    def _csrf_token(self, path: str) -> str:
        """CSRF-токен со страницы (мета-тег `csrf-token`) — нужен для form/DELETE."""
        resp = self.client.session.get(self._url(path), timeout=self.client.timeout)
        expect_status(resp, 200)
        match = _CSRF_META_RE.search(resp.text)
        if not match:
            raise AssertionError(f"Не найден CSRF-токен на странице {path}")
        return match.group(1)

    def _submit_form(
        self,
        path: str,
        data: Dict,
        token_path: Optional[str] = None,
        method_override: Optional[str] = None,
    ) -> requests.Response:
        """POST формы Backpack CRUD (urlencoded, с CSRF и служебными скрытыми полями),
        как это делает браузер при сабмите create/edit-формы."""
        source_path = token_path or path
        token = self._csrf_token(source_path)
        body = {
            "_token": token,
            "_http_referrer": self._url(source_path),
            "_save_action": "save_and_back",
            **data,
        }
        if method_override:
            body["_method"] = method_override
        resp = self.client.session.post(
            self._url(path),
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "text/html, application/json, text/javascript, */*; q=0.01",
                "Referer": self._url(source_path),
            },
            timeout=self.client.timeout,
        )
        return resp

    def _delete(self, path: str, list_path: str) -> requests.Response:
        """DELETE сущности Backpack CRUD (`data-route` иконки-корзины)."""
        token = self._csrf_token(list_path)
        resp = self.client.session.delete(
            self._url(path),
            headers={
                "X-CSRF-TOKEN": token,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": self._url(list_path),
            },
            timeout=self.client.timeout,
        )
        return resp

    def _search(self, path: str, search_value: str = "", start: int = 0, length: int = 25, draw: int = 1) -> Dict:
        """POST {path}/search — те же параметры DataTables, что шлёт браузер при живом
        поиске/пагинации списка; ответ — {"data": [[...HTML ячеек...]], ...}."""
        resp = self.client.session.post(
            self._url(f"{path}/search"),
            data={
                "draw": draw,
                "start": start,
                "length": length,
                "search[value]": search_value,
                "search[regex]": "false",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=self.client.timeout,
        )
        expect_status(resp, 200)
        return resp.json()

    @staticmethod
    def _extract_id(row_html: str) -> Optional[int]:
        """ID сущности из ссылки действия (edit/show/data-route) в HTML-ячейке строки
        результата поиска — создание формы не возвращает ID напрямую (см. find_by_title
        в api/endpoints/tickets.py — тот же приём "найти то, что только что создали")."""
        match = _ROW_ID_RE.search(row_html)
        return int(match.group(1)) if match else None

    def _find_by_name(self, path: str, name: str) -> Optional[Dict]:
        data = self._search(path, search_value=name)
        for row in data.get("data", []):
            row_html = "".join(row)
            if name in row_html:
                return {"id": self._extract_id(row_html), "row_html": row}
        return None

    # ---- Группы (/admin/group) ----

    def create_group(self, payload: Dict) -> requests.Response:
        """Создание группы (payload — generate_helpdesk_group_payload(), с фиктивными
        IMAP/SMTP). Не создавать без фиктивных реквизитов и не трогать системные группы."""
        resp = self._submit_form(self.GROUP_PATH, payload, token_path=f"{self.GROUP_PATH}/create")
        logger.info(f"Helpdesk group create requested: name={payload.get('name')}")
        return resp

    def find_group_by_name(self, name: str) -> Optional[Dict]:
        """Найти группу по точному названию (через тот же /search, что живой поиск в таблице)."""
        return self._find_by_name(self.GROUP_PATH, name)

    def get_group(self, group_id: int) -> str:
        """HTML карточки просмотра группы (/admin/group/{id}/show)."""
        resp = self.client.session.get(self._url(f"{self.GROUP_PATH}/{group_id}/show"), timeout=self.client.timeout)
        expect_status(resp, 200)
        return resp.text

    def update_group(self, group_id: int, payload: Dict) -> requests.Response:
        """Редактирование группы (PUT через `_method`, как в браузере)."""
        edit_path = f"{self.GROUP_PATH}/{group_id}/edit"
        resp = self._submit_form(f"{self.GROUP_PATH}/{group_id}", payload, token_path=edit_path, method_override="PUT")
        logger.info(f"Helpdesk group update requested: id={group_id}")
        return resp

    def delete_group(self, group_id: int) -> requests.Response:
        """Удаление группы — только свои Автотест_*, системные группы не трогать."""
        resp = self._delete(f"{self.GROUP_PATH}/{group_id}", list_path=self.GROUP_PATH)
        logger.info(f"Helpdesk group delete requested: id={group_id}, status={resp.status_code}")
        return resp

    # ---- Шаблоны (/admin/mail-template) ----

    def create_template(self, payload: Dict) -> requests.Response:
        """Создание шаблона ответа (payload — generate_helpdesk_template_payload())."""
        resp = self._submit_form(self.TEMPLATE_PATH, payload, token_path=f"{self.TEMPLATE_PATH}/create")
        logger.info(f"Helpdesk template create requested: name={payload.get('name')}")
        return resp

    def find_template_by_name(self, name: str) -> Optional[Dict]:
        return self._find_by_name(self.TEMPLATE_PATH, name)

    def get_template(self, template_id: int) -> str:
        resp = self.client.session.get(self._url(f"{self.TEMPLATE_PATH}/{template_id}/show"), timeout=self.client.timeout)
        expect_status(resp, 200)
        return resp.text

    def update_template(self, template_id: int, payload: Dict) -> requests.Response:
        """Редактирование шаблона. Реальный маршрут — `{id}/edit` (у выгрузки Test IT v.2
        в кейсе 9623 ошибочно указан .../create — см. docs/helpdesk_recon.md)."""
        edit_path = f"{self.TEMPLATE_PATH}/{template_id}/edit"
        resp = self._submit_form(
            f"{self.TEMPLATE_PATH}/{template_id}", payload, token_path=edit_path, method_override="PUT"
        )
        logger.info(f"Helpdesk template update requested: id={template_id}")
        return resp

    def delete_template(self, template_id: int) -> requests.Response:
        resp = self._delete(f"{self.TEMPLATE_PATH}/{template_id}", list_path=self.TEMPLATE_PATH)
        logger.info(f"Helpdesk template delete requested: id={template_id}, status={resp.status_code}")
        return resp

    # ---- Пользователи (/admin/user) ----

    def search_user(self, query: str) -> Dict:
        """Сырой ответ DataTables-поиска по пользователям.

        ВНИМАНИЕ (см. docs/helpdesk_recon.md §5, кандидат в дефект): многословная
        строка с пробелом в `query` стабильно валит `POST /admin/user/search` в
        HTTP 500 на бэкенде (`Undefined array key "data"`). Этот метод не глушит
        такой ответ — он падает на expect_status, чтобы вызывающий тест мог сам
        решить, обрабатывать это как `xfail` или как баг."""
        resp = self.client.session.post(
            self._url(f"{self.USER_PATH}/search"),
            data={"draw": 1, "start": 0, "length": 25, "search[value]": query, "search[regex]": "false"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=self.client.timeout,
        )
        expect_status(resp, 200)
        return resp.json()

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Найти пользователя по точному email (поиск по email фильтрует с первого
        символа, в отличие от ФИО — см. docs/helpdesk_recon.md, кейс 9605)."""
        return self._find_by_name(self.USER_PATH, email)

    def get_user(self, user_id: int) -> str:
        resp = self.client.session.get(self._url(f"{self.USER_PATH}/{user_id}/show"), timeout=self.client.timeout)
        expect_status(resp, 200)
        return resp.text

    def assign_role(self, user_id: int, payload: Dict) -> requests.Response:
        """Назначение роли(ей) пользователю — payload из
        generate_helpdesk_role_assignment_payload() (`roles[admin|support|group_admin]`,
        подтверждено разведкой буквально). Форма физически открывается в
        iframe-модалке (/admin/user/{id}/assign-role), но URL формы/сабмита тот же."""
        path = f"{self.USER_PATH}/{user_id}/assign-role"
        resp = self._submit_form(path, payload, token_path=path)
        logger.info(f"Helpdesk assign-role requested: user_id={user_id}, payload={payload}")
        return resp

    # ---- Заявители (/admin/identity) ----

    def search_applicant(self, query: str) -> Dict:
        """Сырой ответ DataTables-поиска по заявителям. Поиск по email требует
        полного совпадения адреса, по ФИО — не фильтрует по одному слову (см.
        docs/helpdesk_recon.md, кейс 9606)."""
        resp = self.client.session.post(
            self._url(f"{self.IDENTITY_PATH}/search"),
            data={"draw": 1, "start": 0, "length": 25, "search[value]": query, "search[regex]": "false"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=self.client.timeout,
        )
        expect_status(resp, 200)
        return resp.json()

    def find_applicant_by_email(self, email: str) -> Optional[Dict]:
        return self._find_by_name(self.IDENTITY_PATH, email)

    def add_applicant(self, payload: Dict) -> requests.Response:
        """Добавление заявителя (payload — generate_helpdesk_applicant_payload())."""
        resp = self._submit_form(self.IDENTITY_PATH, payload, token_path=f"{self.IDENTITY_PATH}/create")
        logger.info(f"Helpdesk applicant create requested: email={payload.get('email')}")
        return resp

    def get_applicant(self, applicant_id: int) -> str:
        resp = self.client.session.get(self._url(f"{self.IDENTITY_PATH}/{applicant_id}/show"), timeout=self.client.timeout)
        expect_status(resp, 200)
        return resp.text

    # ---- Тикеты (/admin/ticket) — список в админке (не путать с пользовательской
    # частью тикетов, api/endpoints/tickets.py, уже покрытой тестами) ----

    def list_tickets(self, search_value: str = "", start: int = 0, length: int = 25) -> Dict:
        """Список обращений в админке (сырой ответ DataTables — ячейки уже HTML)."""
        return self._search(self.TICKET_PATH, search_value=search_value, start=start, length=length)
