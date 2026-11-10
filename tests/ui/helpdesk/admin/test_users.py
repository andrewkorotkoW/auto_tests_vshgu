"""UI: назначение роли пользователю из списка (/admin/user,
docs/test_cases/helpdesk/users.md TC-HELPDESK_USERS-006). Роль назначается только своему
тестовому пользователю, не существующим.

Список `/admin/user` — не все пользователи портала, а пользователи ЛМС с ролью
«Администратор» (role_id=1): свежий пользователь без ролей в нём не появляется вовсе
(проверено на develop 11.11.2026, см. docstring tests/api/helpdesk/test_users_api.py).
Поэтому тест берёт `created_helpdesk_user` (корневой conftest.py) — created_user + роль
admin в ЛМС. До 11.11 тест был под xfail «пользователь не в списке + поиск отвечает 500»:
500 на стенде исправили, а «не в списке» оказалось неверным предусловием, не дефектом."""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.helpdesk_users_page import HelpdeskUsersPage


@allure.feature("Хелпдеск: Пользователи")
@allure.story("Назначение роли через форму")
@allure.title("UI: роль назначается тестовому пользователю из списка через модалку с чекбоксами")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
def test_assign_role(admin_page, helpdesk_ui_base_url, created_helpdesk_user):
    user = created_helpdesk_user()
    page = HelpdeskUsersPage(admin_page)
    page.open(helpdesk_ui_base_url)

    with allure.step("Найти тестового пользователя в таблице по email"):
        page.search(user["email"])
        # результат поиска приходит AJAX-ом без индикатора загрузки — ждём строку, а не
        # проверяем count() сразу после wait_loaded()
        expect(page.row(user["email"])).to_be_visible(timeout=15000)

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
    пользователе (см. existing_helpdesk_user_id) — создавать своего не нужно.

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
