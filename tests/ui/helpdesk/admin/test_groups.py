"""UI: CRUD группы хелпдеска через форму (/admin/group, docs/test_cases/helpdesk/groups.md
TC-HELPDESK_GROUPS-003/007). Группа — своя Автотест_* с фиктивными IMAP/SMTP (см.
api.helpers.data_generator.generate_helpdesk_group_payload), системные группы не трогаем.

Исходный дефект (labels без for/id — get_by_label не находил поля; динамический id
#crudTable_<hash> у таблицы групп) исправлен в ui/pages/helpdesk_groups_page.py и
ui/pages/helpdesk_base_page.py задачей t1: fill_create_form() переведён на локатор по
bp-field-name, table()/row() — на table.dataTable с фильтром непустого tbody."""
import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_group_payload
from ui.pages.helpdesk_groups_page import HelpdeskGroupsPage


@allure.feature("Хелпдеск: Группы")
@allure.story("Создание группы через форму")
@allure.title("UI: группа создаётся через форму «Добавить группу» и видна в таблице")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
def test_create_group(admin_page, helpdesk_ui_base_url):
    page = HelpdeskGroupsPage(admin_page)
    page.open(helpdesk_ui_base_url)
    payload = generate_helpdesk_group_payload()

    try:
        with allure.step("Заполнить форму «Добавить группу» и сохранить"):
            page.create_group(payload)
    finally:
        if page.row(payload["name"]).count() > 0:
            with allure.step("Teardown: удалить созданную тестовую группу"):
                page.delete_group(payload["name"])


@allure.feature("Хелпдеск: Группы")
@allure.story("Удаление группы через форму")
@allure.title("UI: группа удаляется через иконку-корзину с подтверждением и пропадает из таблицы")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
def test_delete_group(admin_page, helpdesk_ui_base_url):
    page = HelpdeskGroupsPage(admin_page)
    page.open(helpdesk_ui_base_url)
    payload = generate_helpdesk_group_payload()

    with allure.step("Подготовка: создать свою тестовую группу через форму"):
        page.create_group(payload)

    with allure.step("Удалить группу через иконку-корзину с подтверждением в модалке"):
        page.delete_group(payload["name"])

    assert page.row(payload["name"]).count() == 0, "Группа всё ещё видна в таблице после удаления"
