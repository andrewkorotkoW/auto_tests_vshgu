"""UI: CRUD группы хелпдеска через форму (/admin/group, docs/test_cases/helpdesk/groups.md
TC-HELPDESK_GROUPS-003/007). Группа — своя Автотест_* с фиктивными IMAP/SMTP (см.
api.helpers.data_generator.generate_helpdesk_group_payload), системные группы не трогаем.

ОБНАРУЖЕННЫЙ ДЕФЕКТ (подтверждён живым прогоном Playwright headless на develop,
безопасен для отчёта, НЕ правим — ui/pages/helpdesk_groups_page.py защищена условиями
задачи): `HelpdeskGroupsPage.fill_create_form()` ищет поля через
`page.get_by_label(<подпись>, exact=True)`, но в реальной разметке формы
`/admin/group/create` `<label>Название</label>` — не обёрнутый label без атрибута `for`,
просто сосед `<input>` без `id` (стандартный рендер поля Laravel Backpack CRUD, без
ручной доработки `for`/`aria-labelledby`). Поэтому у Playwright нет способа связать
подпись с полем: `get_by_label(...)` стабильно находит 0 элементов и
`fill_create_form()`/`create_group()` падает по таймауту на самом первом поле
(`Locator.fill: Timeout 30000ms exceeded... waiting for get_by_label("Название")`).
Это тот же паттерн разметки, что и у шаблонов (см. test_templates.py) — похоже на
общий дефект вёрстки форм Backpack CRUD в хелпдеске, а не на что-то специфичное для
группы.

Второй, независимый дефект (см. также test_navigation.py): даже если бы labels были
исправлены, `row()`/`delete_row()` из `HelpdeskAdminPage` (ui/pages/helpdesk_base_page.py)
искали бы строку внутри `#crudTable` — а у /admin/group реальный id таблицы с динамическим
хеш-суффиксом (`crudTable_<hash>`), не статический `#crudTable` — то есть `create_group()`
(финальная проверка строки) и `delete_group()` не сработали бы и после фикса labels."""
import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_group_payload
from ui.pages.helpdesk_groups_page import HelpdeskGroupsPage

_LABEL_DEFECT_REASON = (
    "Дефект вёрстки формы /admin/group/create (не в зоне правки — ui/pages/helpdesk_groups_page.py "
    "защищена условиями задачи): <label>Название</label> и аналогичные подписи полей — не связаны "
    "с <input> ни через for/id, ни через обёртку (просто соседние элементы в одном div), поэтому "
    "page.get_by_label(..., exact=True), который использует fill_create_form(), стабильно находит "
    "0 элементов. Подтверждено живым прогоном Playwright headless на develop: "
    "Locator.fill падает по таймауту 30с на get_by_label(\"Название\")."
)


@allure.feature("Хелпдеск: Группы")
@allure.story("Создание группы через форму")
@allure.title("UI: группа создаётся через форму «Добавить группу» и видна в таблице")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
@pytest.mark.xfail(strict=False, reason=_LABEL_DEFECT_REASON)
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
@pytest.mark.xfail(
    strict=False,
    reason=f"Предусловие (своя тестовая группа) недостижимо: {_LABEL_DEFECT_REASON}",
)
def test_delete_group(admin_page, helpdesk_ui_base_url):
    page = HelpdeskGroupsPage(admin_page)
    page.open(helpdesk_ui_base_url)
    payload = generate_helpdesk_group_payload()

    with allure.step("Подготовка: создать свою тестовую группу через форму"):
        page.create_group(payload)

    with allure.step("Удалить группу через иконку-корзину с подтверждением в модалке"):
        page.delete_group(payload["name"])

    assert page.row(payload["name"]).count() == 0, "Группа всё ещё видна в таблице после удаления"
