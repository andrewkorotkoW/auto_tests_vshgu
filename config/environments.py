"""Слой окружений: develop / stage / prod.

Значения читаются из .env через os.getenv с префиксами <ENV>_...
(например DEVELOP_API_URL, STAGE_COOKIE, PROD_LPD_JWT). Хардкод-хосты,
которые раньше были разбросаны по config/settings.py и тестам, теперь
живут только тут — как значения по умолчанию, если переменная не задана.
"""
import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv

from utils.logger import logger

load_dotenv()

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


@dataclass(frozen=True)
class Environment:
    name: str
    api_base_url: str
    ui_base_url: str
    cookie_name: str
    cookie: str
    global_base_url: str
    cas_auth_token: str
    external_system_client_token: str
    lpd_jwt_token: str
    buk_token: str = ""  # JWT интеграции БУК (<ENV>_BUK_TOKEN), без Bearer


def _getenv_with_legacy(new_name: str, legacy_name: Optional[str], default: str) -> str:
    """Читает новое имя переменной (<ENV>_...), а если оно не задано — старое плоское
    имя (BASE_URL, CAS_AUTH_TOKEN и т.п.), которое могло уже быть в существующем .env.
    """
    value = os.getenv(new_name)
    if value is not None:
        return value
    if legacy_name is not None:
        value = os.getenv(legacy_name)
        if value is not None:
            return value
    return default


def _build_environment(
    name: str,
    cookie_name: str,
    default_api: str,
    default_ui: str,
    default_global: str,
    legacy: Optional[dict] = None,
) -> Environment:
    prefix = name.upper()
    legacy = legacy or {}
    return Environment(
        name=name,
        api_base_url=_getenv_with_legacy(f"{prefix}_API_URL", legacy.get("api_base_url"), default_api),
        ui_base_url=_getenv_with_legacy(f"{prefix}_UI_URL", legacy.get("ui_base_url"), default_ui),
        cookie_name=os.getenv(f"{prefix}_COOKIE_NAME", cookie_name),
        cookie=_getenv_with_legacy(f"{prefix}_COOKIE", legacy.get("cookie"), ""),
        global_base_url=_getenv_with_legacy(f"{prefix}_GLOBAL_URL", legacy.get("global_base_url"), default_global),
        cas_auth_token=_getenv_with_legacy(f"{prefix}_CAS_TOKEN", legacy.get("cas_auth_token"), ""),
        external_system_client_token=_getenv_with_legacy(
            f"{prefix}_EXTERNAL_TOKEN", legacy.get("external_system_client_token"), ""
        ),
        lpd_jwt_token=_getenv_with_legacy(f"{prefix}_LPD_JWT", legacy.get("lpd_jwt_token"), ""),
        buk_token=os.getenv(f"{prefix}_BUK_TOKEN", ""),
    )


ENVIRONMENTS = {
    "develop": _build_environment(
        "develop",
        cookie_name="develop",
        default_api="https://portal-develop.d2.devspark.ru/api/v1",
        default_ui="https://portal-develop.d2.devspark.ru",
        default_global="https://global-develop.d2.devspark.ru/api/v1",
        legacy={
            "api_base_url": "BASE_URL",
            "ui_base_url": "UI_BASE_URL",
            "cookie": "DEVELOP_COOKIE",
            "global_base_url": "GLOBAL_BASE_URL",
            "cas_auth_token": "CAS_AUTH_TOKEN",
            "external_system_client_token": "EXTERNAL_SYSTEM_CLIENT_TOKEN",
            "lpd_jwt_token": "LPD_JWT_TOKEN",
        },
    ),
    "stage": _build_environment(
        "stage",
        cookie_name="stage",
        default_api="https://portal.stage.gosedu.ru/api/v1",
        default_ui="https://portal.stage.gosedu.ru",
        default_global="https://global-stage.d7.devspark.ru/api/v1",
        legacy={
            "api_base_url": "STAGE_BASE_URL",
            "ui_base_url": "STAGE_UI_BASE_URL",
            "cookie": "STAGE_DEVELOP_COOKIE",
            # Токены интеграций на develop и stage общие — если STAGE_* не заданы,
            # берём те же плоские имена, что и для develop.
            "cas_auth_token": "CAS_AUTH_TOKEN",
            "external_system_client_token": "EXTERNAL_SYSTEM_CLIENT_TOKEN",
            "lpd_jwt_token": "LPD_JWT_TOKEN",
        },
    ),
    "prod": _build_environment(
        "prod",
        cookie_name="prod",
        default_api="",
        default_ui="",
        default_global="",
    ),
}

# prod по умолчанию выключен — на нём разрешено гонять только smoke-тесты,
# чтобы случайный полный прогон не выполнял мутирующие тесты на проде.
PROD_ALLOWED_MARKEXPR = "smoke"


def ensure_prod_allowed(env_name: str, markexpr: str) -> None:
    """Бросает понятную ошибку, если для --env=prod не передан -m smoke."""
    if env_name != "prod":
        return
    if (markexpr or "").strip() != PROD_ALLOWED_MARKEXPR:
        raise RuntimeError(
            "Запуск тестов на prod отключён по умолчанию. "
            "Разрешены только smoke-тесты: добавьте флаг `-m smoke` "
            "(например: pytest --env=prod -m smoke)."
        )


class LoginError(RuntimeError):
    """Не удалось авторизоваться на портале по логину/паролю."""


def _extract_csrf_token(html: str) -> Optional[str]:
    match = re.search(r'name="_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else None


class _TenantLinkParser(HTMLParser):
    """Извлекает ссылки выбора организации из страницы tenant-select."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._in_tenant_form = False
        self._tenant_form_depth = 0
        self._current_href = None
        self._current_text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())

        if "tenant-form" in classes:
            self._in_tenant_form = True
            self._tenant_form_depth = 1
        elif self._in_tenant_form:
            self._tenant_form_depth += 1

        if self._in_tenant_form and tag == "a":
            self._current_href = attrs.get("href")
            self._current_text = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            text = " ".join("".join(self._current_text).split())
            self.links.append((text, self._current_href))
            self._current_href = None
            self._current_text = []

        if self._in_tenant_form:
            self._tenant_form_depth -= 1
            if self._tenant_form_depth == 0:
                self._in_tenant_form = False


def _select_tenant_if_required(session: requests.Session, response: requests.Response, env: Environment):
    """Завершает web-сессию выбором ВШГУ, если сервер показал tenant-select."""
    if "/auth/tenant/select" not in response.url and "tenant-form" not in response.text:
        return response

    parser = _TenantLinkParser()
    parser.feed(response.text)
    if not parser.links:
        raise LoginError("Сервер показал выбор организации, но ссылки тенантов не найдены")

    target_domain = urlparse(env.ui_base_url).hostname or ""

    def link_score(link):
        text, href = link
        value = f"{text} {href}".lower()
        return (
            (3 if target_domain.lower() in value else 0)
            + (2 if re.search(r"вшгу|высшая школа государственного управления", value, re.I) else 0)
        )

    tenant_text, tenant_href = max(parser.links, key=link_score)
    if link_score((tenant_text, tenant_href)) == 0 and len(parser.links) > 1:
        raise LoginError("Не удалось однозначно выбрать тенант ВШГУ после авторизации")

    selected = session.get(
        urljoin(response.url, tenant_href),
        headers={"Referer": response.url},
        timeout=30,
        allow_redirects=True,
    )
    if selected.status_code >= 400:
        raise LoginError(f"Не удалось выбрать тенант ВШГУ: HTTP {selected.status_code}")
    return selected


def login(env: Environment, email: str, password: str) -> requests.Session:
    """Логинится на портале так же, как это делает браузер: получает CSRF-токен
    со страницы /auth/main и отправляет POST /auth/login формой. Сессионная
    кука выставляется самим сервером в session.cookies.
    """
    session = requests.Session()
    login_page_url = f"{env.ui_base_url}/auth/main"
    login_page = session.get(login_page_url, timeout=30)
    token = _extract_csrf_token(login_page.text)
    if not token:
        raise LoginError(f"Не найден CSRF-токен на странице логина {login_page_url}")

    response = session.post(
        f"{env.ui_base_url}/auth/login",
        data={"_token": token, "email_or_login": email, "password": password},
        headers={"Referer": login_page_url},
        timeout=30,
        allow_redirects=True,
    )

    if "login-form" in response.text:
        raise LoginError(
            f"Логин на {env.name} не удался: сервер вернул форму логина обратно "
            "(неверные учётные данные или сработала защита от логина)."
        )

    _select_tenant_if_required(session, response, env)
    return session


def _cache_path(env_name: str, role: str) -> Path:
    return CACHE_DIR / f"session_{env_name}_{role}.json"


def _load_cached_session(env_name: str, role: str) -> Optional[requests.Session]:
    path = _cache_path(env_name, role)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    session = requests.Session()
    for cookie in data.get("cookies", []):
        session.cookies.set(
            cookie["name"], cookie["value"], domain=cookie.get("domain"), path=cookie.get("path", "/")
        )
    return session


def _store_cached_session(env_name: str, role: str, session: requests.Session) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cookies = [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
        for c in session.cookies
    ]
    _cache_path(env_name, role).write_text(json.dumps({"cookies": cookies}))


def _session_is_valid(env: Environment, session: requests.Session) -> bool:
    try:
        resp = session.get(
            f"{env.api_base_url}/auth/me",
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_credentials(env_name: str, role: str = "default") -> Tuple[Optional[str], Optional[str]]:
    """Читает логин/пароль для роли из .env: <ENV>_<ROLE>_LOGIN/PASSWORD.

    role="default" читает <ENV>_LOGIN/<ENV>_PASSWORD, а для develop дополнительно
    падает обратно на DEFAULT_LOGIN/DEFAULT_PASSWORD (уже существующая учётка).
    role="admin"/"user" падают обратно на учётку role="default", если своя не задана.
    """
    prefix = env_name.upper()
    if role == "default":
        login_ = os.getenv(f"{prefix}_LOGIN")
        password_ = os.getenv(f"{prefix}_PASSWORD")
        if env_name == "develop":
            login_ = login_ or os.getenv("DEFAULT_LOGIN")
            password_ = password_ or os.getenv("DEFAULT_PASSWORD")
        return login_, password_

    role_prefix = f"{prefix}_{role.upper()}"
    login_ = os.getenv(f"{role_prefix}_LOGIN")
    password_ = os.getenv(f"{role_prefix}_PASSWORD")
    if login_ and password_:
        return login_, password_
    return get_credentials(env_name, role="default")


def get_session(env: Environment, role: str = "default", use_cache: bool = True) -> requests.Session:
    """Возвращает авторизованную сессию для окружения/роли.

    Порядок: валидный кэш в .cache/ → логин по логину/паролю из .env (с кэшированием
    результата) → ручная кука <ENV>_COOKIE как запасной вариант (с предупреждением).
    """
    if use_cache:
        cached = _load_cached_session(env.name, role)
        if cached is not None and _session_is_valid(env, cached):
            return cached

    email, password = get_credentials(env.name, role)
    if email and password:
        try:
            session = login(env, email, password)
            if _session_is_valid(env, session):
                if use_cache:
                    _store_cached_session(env.name, role, session)
                return session
            logger.warning(
                f"Логин на {env.name} прошёл без ошибки, но /auth/me не подтвердил сессию — "
                "используем запасной вариант."
            )
        except LoginError as exc:
            logger.warning(f"{exc} Используем запасной вариант (ручная кука), если она задана.")

    if env.cookie:
        logger.warning(
            f"Используется ручная кука {env.cookie_name.upper()}_COOKIE для {env.name} — "
            "она может быть устаревшей, задайте логин/пароль в .env, чтобы избежать этого."
        )
        session = requests.Session()
        session.cookies.set(env.cookie_name, env.cookie)
        return session

    raise LoginError(
        f"Нет способа авторизоваться на {env.name}: не заданы ни {env.name.upper()}_LOGIN/"
        f"{env.name.upper()}_PASSWORD, ни {env.name.upper()}_COOKIE."
    )


def _storage_state_path(env_name: str, role: str) -> Path:
    return CACHE_DIR / f"storage_state_{env_name}_{role}.json"


def build_storage_state(env: Environment, session: requests.Session) -> dict:
    """Преобразует куки requests.Session в формат Playwright storage_state,
    чтобы не логиниться через UI-форму на каждый тест."""
    domain = env.ui_base_url.split("://", 1)[-1].split("/", 1)[0]
    cookies = []
    for cookie in session.cookies:
        cookies.append({
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain or domain,
            "path": cookie.path or "/",
            "expires": cookie.expires if cookie.expires else -1,
            "httpOnly": bool(cookie._rest.get("HttpOnly", False)) if hasattr(cookie, "_rest") else False,
            "secure": bool(cookie.secure),
            "sameSite": "Lax",
        })
    return {"cookies": cookies, "origins": []}


def get_storage_state_path(env: Environment, role: str = "default") -> Path:
    """Возвращает путь к закэшированному Playwright storage_state для окружения/роли,
    логинясь и сохраняя его в .cache/, если кэша ещё нет или сессия невалидна."""
    path = _storage_state_path(env.name, role)
    session = get_session(env, role=role)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_storage_state(env, session)))
    return path
