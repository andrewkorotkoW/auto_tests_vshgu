"""UI: назначение роли пользователю из списка (/admin/user,
docs/test_cases/helpdesk/users.md TC-HELPDESK_USERS-006). Роль назначается только своему
тестовому пользователю (`created_user` из корневого conftest.py), не существующим.

ОБНАРУЖЕННЫЙ БЛОКЕР (подтверждён живыми запросами к develop, не чиним — выходит за рамки
UI-трека и за рамки правок, разрешённых в этой задаче):
1. Список `/admin/user` — это не все пользователи портала, а только уже «известные»
   хелпдеску (recordsTotal не меняется: 49 до и 49 после создания нового пользователя
   через POST /api/v1/users). Свежесозданный `created_user` в этом списке не появляется
   вовсе, его не находит ни поиск, ни прямой проход по первой странице таблицы.
2. Даже если бы строка появилась, `POST /admin/user/search` отвечает HTTP 500
   (`Undefined array key "data"`, `UserCrudController.php:82`) на любой запрос,
   не находящий совпадений в этом коротком списке, — тот же дефект шире, что в
   tests/api/helpdesk/test_users_api.py::TestUsersApi::test_assign_role (тот же
   контроллер, то же примечание в docs/helpdesk_recon.md §5.1).
Тест написан по контракту page-объекта (ищет пользователя через HelpdeskUsersPage.search,
затем open_assign_role_modal/assign_roles) — ожидаемо не проходит из-за блокера выше."""
import allure
import pytest

from ui.pages.helpdesk_users_page import HelpdeskUsersPage

_USER_NOT_LISTED_REASON = (
    'Блокер подтверждён живыми запросами на develop: свежесозданный через API пользователь '
    '(created_user) не появляется в списке /admin/user вообще (recordsTotal не меняется — '
    '49 до и после создания), а POST /admin/user/search отвечает HTTP 500 '
    '(\'Undefined array key "data"\', UserCrudController.php:82) на запрос без совпадений — '
    'тот же дефект, что в tests/api/helpdesk/test_users_api.py::TestUsersApi::test_assign_role. '
    'Назначить роль тестовому пользователю через UI невозможно до исправления бэкенда.'
)


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Назначение роли через форму")
@allure.title("UI: роль назначается тестовому пользователю из списка через модалку с чекбоксами")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
@pytest.mark.xfail(strict=False, reason=_USER_NOT_LISTED_REASON)
def test_assign_role(admin_page, helpdesk_ui_base_url, created_user):
    user = created_user()
    page = HelpdeskUsersPage(admin_page)
    page.open(helpdesk_ui_base_url)

    with allure.step("Найти тестового пользователя в таблице по email"):
        page.search(user["email"])
        row = page.row(user["email"])
        assert row.count() > 0, f"Тестовый пользователь {user['email']!r} не найден в списке /admin/user"

    with allure.step("Открыть модалку назначения ролей и отметить «Поддержка»"):
        page.open_assign_role_modal(user["id"])
        page.assign_roles(support=True)

    with allure.step("Проверить назначенную роль в карточке пользователя"):
        page.open_show_page(helpdesk_ui_base_url, user["id"])
        assert "оддержк" in admin_page.content(), "Назначенная роль «Поддержка» не отображается в карточке"
