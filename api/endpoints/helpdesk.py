import re
from typing import Dict, Optional

import requests

from api.client import ApiClient
from api.helpers.expectations import expect_status
from utils.logger import logger

# На develop мета-тег самозакрывающийся (`content="..."/>`), на других сборках может быть `">` —
# допускаем оба варианта, иначе _csrf_token() не находит токен ни на одной странице.
_CSRF_META_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)"\s*/?>')
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

    Реальные `name`-атрибуты полей подтверждены Playwright-разведкой по живым формам на
    develop (не всегда совпадают с конвенцией snake_case от подписи): группа —
    `ticket_prefix` (не `prefix`), `password` (не `imap_password`); шаблон — обязательный
    скрытый `type=user` и `groups[]` (не `group_ids`); заявитель — `wave` (не `stream_id`).
    `generate_helpdesk_*_payload()` в api/helpers/data_generator.py намеренно оставлены со
    старыми «логическими» именами ключей (их проверяют тесты через `payload["prefix"]` и
    т.п.) — перевод в реальные имена полей формы делает `_to_group_form_data`/
    `_to_template_form_data`/`_to_applicant_form_data` внутри create_*/update_*.

    Контракт `_submit_form` (критично для негативных тестов): сервер решает, вернуть ли
    422 JSON с полем `errors` или перенаправить(302)/отрендерить форму заново (200 HTML) —
    по заголовку `Accept` запроса (`Request::wantsJson()` в Laravel смотрит на ПЕРВЫЙ тип в
    Accept). Если `Accept` начинается с `application/json` — валидационная ошибка всегда
    приходит как 422 JSON; если с `text/html` — как редирект с флеш-ошибками в сессии (как
    реально ведёт себя настоящий браузер при сабмите этих форм, подтверждено перехватом
    трафика: реальный клиент вообще не шлёт AJAX-заголовки на create/edit-формах). Здесь
    выбран режим с `Accept: application/json, ...` в приоритете — он даёт разбираемый 422 и
    работает для шаблонов/заявителей/назначения ролей, но для ГРУПП вскрывает отдельный,
    не связанный с CSRF дефект стенда: `GroupCrudController::store()`/`update()` на успехе
    (валидные данные) бросает `TypeError: Return value must be of type RedirectResponse,
    JsonResponse returned` (500) при `wantsJson()==true`, хотя запись в БД всё равно
    создаётся/обновляется — см. коммит с деталями. `ApiClient.__init__` уже выставляет
    `Accept: application/json`/`X-Requested-With: XMLHttpRequest` на уровне `session.headers`
    — любой прямой `client.session.post(...)` без явного собственного `headers=` неявно
    наследует эти значения.

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
            # Реальная форма редактирования шлёт скрытое поле `id` ПОМИМО id в самом URL —
            # без него update-маршрут отвечает 404 "No query results for model" даже для
            # заведомо существующей записи (подтверждено живым прогоном: GET /edit и DELETE
            # по тому же id работают, а PUT без `id` в теле — нет). id берём из хвоста path
            # (".../{id}" для update-запроса).
            id_match = re.search(r"/(\d+)$", path)
            if id_match:
                body.setdefault("id", id_match.group(1))
        resp = self.client.session.post(
            self._url(path),
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                # `application/json` ПЕРВЫМ — иначе Laravel Request::wantsJson() считает,
                # что клиент хочет HTML, и на ошибке валидации делает redirect-back (200/302
                # с флеш-ошибками в сессии) вместо разбираемого 422 JSON с полем `errors`.
                "Accept": "application/json, text/javascript, */*; q=0.01",
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
        """Первая строка отфильтрованного сервером результата /search (не делает собственную
        подстрочную проверку текста ячейки — сервер и так фильтрует по полному значению
        search[value], а колонки списка могут обрезать длинные значения многоточием при
        отображении: подтверждено живым прогоном — `name in row_html` не находил
        свежесозданный шаблон/группу с достаточно длинным именем из-за этой обрезки)."""
        data = self._search(path, search_value=name)
        rows = data.get("data", [])
        if not rows:
            return None
        row_html = "".join(rows[0])
        return {"id": self._extract_id(row_html), "row_html": rows[0]}

    @staticmethod
    def _to_group_form_data(payload: Dict) -> Dict:
        """Логические ключи generate_helpdesk_group_payload() -> реальные name-атрибуты
        формы /admin/group/create (подтверждено Playwright: `prefix` -> `ticket_prefix`,
        `imap_password` -> `password`, остальные совпадают буквально). Ключи payload
        намеренно не переименованы в генераторе — тесты читают payload["prefix"]."""
        data = dict(payload)
        if "prefix" in data:
            data["ticket_prefix"] = data.pop("prefix")
        if "imap_password" in data:
            data["password"] = data.pop("imap_password")
        if "users_collection" in data:
            data["users_collection[]"] = data.pop("users_collection")
        return data

    # ---- Группы (/admin/group) ----

    def create_group(self, payload: Dict) -> requests.Response:
        """Создание группы (payload — generate_helpdesk_group_payload(), с фиктивными
        IMAP/SMTP). Не создавать без фиктивных реквизитов и не трогать системные группы.

        ВНИМАНИЕ (дефект стенда, не infra): на успешном создании/редактировании с
        `Accept: application/json` (нужен для разбираемого 422 на невалидных данных, см.
        докстринг класса) `GroupCrudController` бросает 500 (TypeError на возврате ответа),
        хотя группа реально создаётся/обновляется в БД — проверять через find_group_by_name,
        а не только по resp.status_code."""
        resp = self._submit_form(
            self.GROUP_PATH, self._to_group_form_data(payload), token_path=f"{self.GROUP_PATH}/create"
        )
        logger.info(f"Helpdesk group create requested: name={payload.get('name')}")
        return resp

    def find_group_by_name(self, name: str) -> Optional[Dict]:
        """Найти группу по точному названию (через тот же /search, что живой поиск в таблице —
        в отличие от /admin/user/search, этот эндпоинт корректно находит свежесозданные записи,
        подтверждено живым прогоном)."""
        return self._find_by_name(self.GROUP_PATH, name)

    def get_group(self, group_id: int) -> str:
        """HTML карточки просмотра группы (/admin/group/{id}/show)."""
        resp = self.client.session.get(self._url(f"{self.GROUP_PATH}/{group_id}/show"), timeout=self.client.timeout)
        expect_status(resp, 200)
        return resp.text

    def update_group(self, group_id: int, payload: Dict) -> requests.Response:
        """Редактирование группы (PUT через `_method`, как в браузере). См. предупреждение
        о дефекте 500-на-успехе в create_group."""
        edit_path = f"{self.GROUP_PATH}/{group_id}/edit"
        resp = self._submit_form(
            f"{self.GROUP_PATH}/{group_id}", self._to_group_form_data(payload), token_path=edit_path, method_override="PUT"
        )
        logger.info(f"Helpdesk group update requested: id={group_id}")
        return resp

    def delete_group(self, group_id: int) -> requests.Response:
        """Удаление группы — только свои Автотест_*, системные группы не трогать."""
        resp = self._delete(f"{self.GROUP_PATH}/{group_id}", list_path=self.GROUP_PATH)
        logger.info(f"Helpdesk group delete requested: id={group_id}, status={resp.status_code}")
        return resp

    @staticmethod
    def _to_template_form_data(payload: Dict) -> Dict:
        """Логические ключи generate_helpdesk_template_payload() -> реальные name-атрибуты
        формы /admin/mail-template/create: обязательный скрытый `type=user` (без него —
        SQLSTATE not-null violation, 500) и `groups[]` вместо `group_ids`."""
        data = dict(payload)
        data.setdefault("type", "user")
        if "group_ids" in data:
            data["groups[]"] = data.pop("group_ids")
        return data

    # ---- Шаблоны (/admin/mail-template) ----

    def create_template(self, payload: Dict) -> requests.Response:
        """Создание шаблона ответа (payload — generate_helpdesk_template_payload())."""
        resp = self._submit_form(
            self.TEMPLATE_PATH, self._to_template_form_data(payload), token_path=f"{self.TEMPLATE_PATH}/create"
        )
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
            f"{self.TEMPLATE_PATH}/{template_id}",
            self._to_template_form_data(payload),
            token_path=edit_path,
            method_override="PUT",
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
        """Добавление заявителя (payload — generate_helpdesk_applicant_payload()). Логический
        ключ `stream_id` переводится в реальное имя поля формы `wave` (подтверждено Playwright:
        /admin/identity/create шлёт `wave`, а не `stream_id`)."""
        data = dict(payload)
        if "stream_id" in data:
            data["wave"] = data.pop("stream_id")
        resp = self._submit_form(self.IDENTITY_PATH, data, token_path=f"{self.IDENTITY_PATH}/create")
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

    # ---- Справочники (категории/теги/типы заявителей/контактов/обращений/результата,
    # чёрный список — 7 штук, один общий CRUD-паттерн, см. HelpdeskDictEndpoint) ----

    def dict_endpoint(self, key: str) -> "HelpdeskDictEndpoint":
        """Фабрика CRUD-обёртки для одного из 7 справочников хелпдеска по ключу
        (см. _DICT_DEFINITIONS): "category", "tag", "applicant_type", "request_source",
        "request_type", "processing_result", "blacklist"."""
        return HelpdeskDictEndpoint(self, key)


_DICT_DEFINITIONS = {
    # Категории/типы заявителей/контактов/обращений/результата и теги — поле «Значение»
    # (name-атрибут `value`, кроме тегов — там `name`), требуют group_id (подтверждено
    # живым прогоном: без group_id сервер отвечает 422 "The group id field is required",
    # хотя разведка по вёрстке посчитала поле необязательным). type — обязательный
    # скрытый дискриминатор, значение совпадает с ключом справочника в БД.
    "category": {
        "list_path": "/admin/dict/category/view/list-category",
        "entity_path": "/admin/dict/category",
        "value_field": "value",
        "type_value": "category",
    },
    "tag": {
        "list_path": "/admin/tag",
        "entity_path": "/admin/tag",
        "value_field": "name",
        "type_value": None,
    },
    "applicant_type": {
        "list_path": "/admin/dict/applicant_type",
        "entity_path": "/admin/dict/applicant_type",
        "value_field": "value",
        "type_value": "applicant_type",
    },
    "request_source": {
        "list_path": "/admin/dict/request_source",
        "entity_path": "/admin/dict/request_source",
        "value_field": "value",
        "type_value": "request_source",
    },
    "request_type": {
        "list_path": "/admin/dict/request_type",
        "entity_path": "/admin/dict/request_type",
        "value_field": "value",
        "type_value": "request_type",
    },
    "processing_result": {
        "list_path": "/admin/dict/processing_result",
        "entity_path": "/admin/dict/processing_result",
        "value_field": "value",
        "type_value": "processing_result",
    },
    "blacklist": {
        "list_path": "/admin/blacklist",
        "entity_path": "/admin/blacklist",
        "value_field": "email",
        "type_value": None,
    },
}


class HelpdeskDictEndpoint:
    """Один параметризуемый CRUD вместо 7 копий для одинаково устроенных справочников
    хелпдеска (разведка, docs/helpdesk_recon.md §3): список → «Добавить N» → форма с полем
    «Значение» (+ опционально «Системная группа» — на деле обязательное, см.
    _DICT_DEFINITIONS) → удаление через иконку-корзину. У чёрного список адресов — поле
    «Почтовый адрес» (`email`) вместо «Значение» и нет group_id.

    `find_by_value` не сравнивает текст ячейки подстрокой (как `HelpdeskEndpoint._find_by_name`)
    — у справочников колонка «Значение» узкая и сервер обрезает длинные значения многоточием
    при отображении (подтверждено живым прогоном: `"Автотест_..." in row_html` не находил
    свежесозданную запись из-за обрезки), поэтому берётся первая строка уже отфильтрованного
    сервером (по полному значению, не отображаемому тексту) результата /search."""

    def __init__(self, endpoint: HelpdeskEndpoint, key: str):
        config = _DICT_DEFINITIONS[key]
        self._endpoint = endpoint
        self.key = key
        self.list_path = config["list_path"]
        self.entity_path = config["entity_path"]
        self.value_field = config["value_field"]
        self.type_value = config["type_value"]

    def _form_data(self, value: str, group_id: Optional[int]) -> Dict:
        data = {self.value_field: value}
        if self.type_value:
            data["type"] = self.type_value
        if group_id is not None:
            data["group_id"] = group_id
        return data

    def create(self, value: str, group_id: int = None) -> requests.Response:
        resp = self._endpoint._submit_form(
            self.entity_path, self._form_data(value, group_id), token_path=f"{self.entity_path}/create"
        )
        logger.info(f"Helpdesk dict[{self.key}] create requested: {self.value_field}={value}")
        return resp

    def find_by_value(self, value: str) -> Optional[Dict]:
        return self._endpoint._find_by_name(self.list_path, value)

    def update(self, item_id: int, value: str, group_id: int = None) -> requests.Response:
        edit_path = f"{self.entity_path}/{item_id}/edit"
        resp = self._endpoint._submit_form(
            f"{self.entity_path}/{item_id}",
            self._form_data(value, group_id),
            token_path=edit_path,
            method_override="PUT",
        )
        logger.info(f"Helpdesk dict[{self.key}] update requested: id={item_id}")
        return resp

    def delete(self, item_id: int) -> requests.Response:
        resp = self._endpoint._delete(f"{self.entity_path}/{item_id}", list_path=self.list_path)
        logger.info(f"Helpdesk dict[{self.key}] delete requested: id={item_id}, status={resp.status_code}")
        return resp
