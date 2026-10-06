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


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Просмотр карточки пользователя")
@allure.title("UI: карточка пользователя показывает ID/ФИО/Email/Роли/Действия")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_view_user_card(admin_page, helpdesk_ui_base_url, existing_helpdesk_user_id):
    """TC-HELPDESK_USERS-002. Карточка проверяется read-only, на уже существующем
    пользователе (см. existing_helpdesk_user_id) — свежесозданный пользователь в списке
    /admin/user не появляется (см. test_assign_role выше).

    НАХОДКА (противоречит примечанию о #9593 в docs/test_cases/helpdesk/users.md,
    подтверждено живым прогоном Playwright на develop на 6+ разных пользователях, не
    правим, только документируем — фактическое изменение docs вне этой задачи):
    примечание файла заявляет, что в блоке «Действия» карточки пользователя осталась
    только иконка «Редактировать», шестерёнка назначения ролей убрана (кейс #9593
    устарел). На деле на develop шестерёнка «Настройка роли»
    (`button[bp-button='assign-role']`) РЕАЛЬНО присутствует в этом блоке наравне с
    иконкой «Редактировать» — то есть сам пункт #9593 не устарел, устарела заметка о
    его устаревании. Тест проверяет фактический контракт (обе кнопки присутствуют), а
    не утверждение из примечания."""
    page = HelpdeskUsersPage(admin_page)

    with allure.step("Открыть карточку пользователя"):
        page.open_show_page(helpdesk_ui_base_url, existing_helpdesk_user_id)
        assert f"/admin/user/{existing_helpdesk_user_id}/show" in admin_page.url

    with allure.step("Проверить блоки ID/ФИО/Email/Роли/Действия"):
        body_text = admin_page.locator("body").inner_text()
        for label in ("ID", "ФИО", "Email", "Роли", "Действия"):
            assert label in body_text, f"На карточке пользователя не найден блок «{label}»"

    with allure.step("В блоке «Действия» есть иконка «Редактировать»"):
        assert admin_page.locator("a[bp-button='update']").count() > 0, (
            "На карточке пользователя не найдена иконка «Редактировать»"
        )


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Настройка таблицы тикетов")
@allure.title("UI: настройка таблицы тикетов пользователя из списка «Список системных пользователей»")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_configure_ticket_table_columns_from_list(
    admin_page, helpdesk_ui_base_url, existing_helpdesk_user_id, restore_ticket_table_columns
):
    """TC-HELPDESK_USERS-003. Настройки отображения — не удаляемая системная сущность,
    но личная настройка конкретного пользователя: читаем исходный список колонок ДО
    изменений и регистрируем его в restore_ticket_table_columns сразу же — восстановление
    гарантировано в teardown фикстуры независимо от исхода теста."""
    page = HelpdeskUsersPage(admin_page)

    with allure.step("Открыть «Настройки таблицы тикетов» через карандаш в списке пользователей"):
        page.open(helpdesk_ui_base_url)
        row = page.row(str(existing_helpdesk_user_id))
        assert row.count() > 0, f"Пользователь id={existing_helpdesk_user_id} не найден в списке /admin/user"
        row.locator("a[bp-button='update']").first.click()
        page.wait_loaded()
        assert f"/admin/user/{existing_helpdesk_user_id}/edit" in admin_page.url

    original_columns = page.get_ticket_table_columns()
    restore_ticket_table_columns(existing_helpdesk_user_id, original_columns)

    new_columns = ["title", "status"]
    with allure.step("Добавить две колонки с разными значениями и сохранить"):
        page.set_ticket_table_columns(new_columns)
        assert f"{helpdesk_ui_base_url.rstrip('/')}/admin/user" == admin_page.url.rstrip("/").split("?")[0], (
            "После сохранения настроек ожидалась страница «Список системных пользователей»"
        )

    with allure.step("Настройки сохранились (round-trip через повторное открытие формы)"):
        page.open_edit_form(helpdesk_ui_base_url, existing_helpdesk_user_id)
        assert page.get_ticket_table_columns() == new_columns, "Сохранённые колонки не совпадают с выбранными"


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Настройка таблицы тикетов")
@allure.title("UI: настройка таблицы тикетов пользователя из его карточки")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_configure_ticket_table_columns_from_card(
    admin_page, helpdesk_ui_base_url, existing_helpdesk_user_id, restore_ticket_table_columns
):
    """TC-HELPDESK_USERS-004. Тот же экран настроек, что и в
    test_configure_ticket_table_columns_from_list, но вход — через иконку «Карандаш» в
    блоке «Действия» карточки пользователя (/admin/user/{id}/show), а не из списка."""
    page = HelpdeskUsersPage(admin_page)

    with allure.step("Открыть карточку пользователя и перейти в «Настройки таблицы тикетов»"):
        page.open_show_page(helpdesk_ui_base_url, existing_helpdesk_user_id)
        admin_page.locator("a[bp-button='update']").first.click()
        page.wait_loaded()
        assert f"/admin/user/{existing_helpdesk_user_id}/edit" in admin_page.url

    original_columns = page.get_ticket_table_columns()
    restore_ticket_table_columns(existing_helpdesk_user_id, original_columns)

    new_columns = ["content", "group_id"]
    with allure.step("Добавить две колонки с разными значениями и сохранить"):
        page.set_ticket_table_columns(new_columns)
        assert f"{helpdesk_ui_base_url.rstrip('/')}/admin/user" == admin_page.url.rstrip("/").split("?")[0], (
            "После сохранения настроек ожидалась страница «Список системных пользователей»"
        )

    with allure.step("Настройки сохранились (round-trip через повторное открытие формы)"):
        page.open_edit_form(helpdesk_ui_base_url, existing_helpdesk_user_id)
        assert page.get_ticket_table_columns() == new_columns, "Сохранённые колонки не совпадают с выбранными"
