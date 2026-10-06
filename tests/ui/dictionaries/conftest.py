"""Фикстуры для UI-тестов справочников в админке (/admin/catalogs/*, см.
ui/pages/admin_dictionaries_page.py и docs/plans/2026-09-25_dictionaries_mission.md).

DICTIONARY_TYPE — program_type («Вид программы»): единственный тип из 6 подстраниц
каталога, для которого мишн-док и API-тесты (tests/api/dictionaries/conftest.py,
SAFE_DICTIONARY_TYPES) подтвердили безопасный round-trip без побочных эффектов —
project/program_level ломают чтение всего типа без meta.experts_entity_id (README §14),
region/municipality — read-only справочники ФИАС на develop, их не создают тестами.

cleanup_dictionary_items — best-effort удаление по имени через API в teardown (страховка
на случай, если тест упал до штатного admin_dictionaries_page.delete_item() — тот же
приём, что и tests/ui/notifications/conftest.py::created_notification).

second_user_page — страница Playwright под реально другим, только что созданным
пользователем (не admin_page/user_page, которые на develop — один и тот же аккаунт с
ролями admin+manager, см. README §13/§14) — нужна, чтобы проверить, что раздел
«Справочники» в админке недоступен обычному слушателю без прав.
"""
import pytest

from api.endpoints.dictionaries import DictionariesEndpoint
from api.helpers.data_generator import unique_suffix
from config.environments import build_storage_state, login
from ui.pages.admin_dictionaries_page import AdminDictionariesPage
from ui.pages.user_sidebar_page import UserSidebarPage
from utils.logger import logger

DICTIONARY_TYPE = "program_type"


@pytest.fixture
def dictionary_type():
    return DICTIONARY_TYPE


@pytest.fixture
def dictionaries_endpoint(api_client):
    return DictionariesEndpoint(api_client)


@pytest.fixture
def dictionary_name():
    def _name(label: str = "") -> str:
        return f"Автотест_UI_справочник_{label}{unique_suffix()}"

    return _name


@pytest.fixture
def admin_dictionaries_page(admin_page, env):
    """Открытая подстраница каталога program_type («Вид программы»), с закрытым
    онбординг-туром — storage_state логинит без формы, поэтому тур ещё не пройден
    (см. tests/ui/practical_tasks/test_create_program_stream_module.py)."""
    page = AdminDictionariesPage(admin_page)
    page.open(env.ui_base_url, DICTIONARY_TYPE)
    UserSidebarPage(admin_page).dismiss_popups()
    return page


@pytest.fixture
def cleanup_dictionary_items(dictionaries_endpoint):
    names = []

    def _track(name: str) -> None:
        names.append(name)

    yield _track

    for name in names:
        try:
            item = dictionaries_endpoint.find_by_name(DICTIONARY_TYPE, name)
            if item:
                dictionaries_endpoint.delete(item["id"])
        except Exception as exc:  # noqa: BLE001 — teardown не должен ронять прогон
            logger.warning(f"Не удалось удалить элемент справочника '{name}': {exc}")


@pytest.fixture
def second_user_page(browser, env, created_user, build_context_kwargs):
    """Страница Playwright, авторизованная под реально другим пользователем (отдельные
    email/пароль, отдельный логин через config.environments.login) — в отличие от
    user_page (общий с admin_page аккаунт на develop), у него нет ролей admin/manager
    (generate_user_payload: roles=None)."""
    user = created_user()
    session = login(env, user["email"], user["password"])
    storage_state = build_storage_state(env, session)
    context = browser.new_context(**build_context_kwargs(storage_state))
    from conftest import _apply_env_timeouts
    _apply_env_timeouts(context, env)
    page = context.new_page()
    yield page
    context.close()
