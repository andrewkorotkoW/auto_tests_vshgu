"""UI: список → создать → отредактировать → удалить для каждого из 7 справочников
хелпдеска (один общий паттерн, ui/pages/helpdesk_dict_page.py), docs/test_cases/helpdesk/
tickets.md TC-HELPDESK_TICKETS-003..009. Создание/удаление — только свои Автотест_*/
auto_test_* записи, системные справочники (и группа, на которую они ссылаются) не
трогаем — HelpdeskDictPage.fill_create_form() выбирает уже существующую системную группу
«Личная группа» в select2 «Системная группа», саму группу не создаёт/не редактирует.

Поле формы и обязательность группы — как в tests/api/helpdesk/test_dictionaries_api.py:
у 6 из 7 справочников поле «Значение» + обязательный select2 «Системная группа», у
«Чёрного списка адресов» — «Почтовый адрес» без группы (has_group=False).

ОБНАРУЖЕННЫЙ ДЕФЕКТ (тот же, что в test_dictionaries_api.py, подтверждён и через UI):
создание записи «Чёрного списка адресов» через форму `/admin/blacklist/create` падает
на стороне сервера (500 при валидации уникальности email) — строка не появляется в
списке, `page.create()` падает по таймауту на ожидании строки после сохранения."""
import allure
import pytest

from api.helpers.data_generator import unique_suffix
from ui.pages.helpdesk_base_page import DELETE_CONFIRM_BUTTON_RE
from ui.pages.helpdesk_dict_page import HelpdeskDictPage

_SYSTEM_GROUP_NAME = "Личная группа"

_BLACKLIST_500_DEFECT_REASON = (
    "Дефект стенда (тот же, что в tests/api/helpdesk/test_dictionaries_api.py, не правим — "
    "ui/pages/helpdesk_dict_page.py защищена условиями задачи): создание записи чёрного "
    "списка падает на сервере 500 при валидации уникальности email, строка не появляется "
    "в списке — page.create() падает по таймауту, ожидая строку после сохранения."
)

_DICT_CASES = [
    pytest.param("category", "Категории", "/admin/dict/category", "value", True, id="category"),
    pytest.param("tag", "Теги", "/admin/tag", "name", True, id="tag"),
    pytest.param(
        "applicant_type", "Типы заявителей", "/admin/dict/applicant_type", "value", True, id="applicant_type"
    ),
    pytest.param(
        "request_source", "Типы контактов", "/admin/dict/request_source", "value", True, id="request_source"
    ),
    pytest.param("request_type", "Типы обращений", "/admin/dict/request_type", "value", True, id="request_type"),
    pytest.param(
        "processing_result",
        "Типы результата",
        "/admin/dict/processing_result",
        "value",
        True,
        id="processing_result",
    ),
    pytest.param(
        "blacklist",
        "Черный список адресов",
        "/admin/blacklist",
        "email",
        False,
        id="blacklist",
        marks=pytest.mark.xfail(strict=False, reason=_BLACKLIST_500_DEFECT_REASON),
    ),
]


def _generate_value(key: str, value_field: str) -> str:
    suffix = unique_suffix()
    if value_field == "email":
        return f"auto_test_blacklist_{suffix}@autotest.invalid"
    return f"Автотест_{key}_{suffix}"


@allure.feature("Хелпдеск: Справочники")
@allure.story("CRUD записи справочника через форму (UI)")
@pytest.mark.ui
@pytest.mark.develop
@pytest.mark.parametrize("key,dict_label,path,value_field,has_group", _DICT_CASES)
def test_dictionary_crud(admin_page, helpdesk_ui_base_url, key, dict_label, path, value_field, has_group):
    allure.dynamic.title(
        f"UI: справочник «{dict_label}» (поле «{'Значение' if value_field != 'email' else 'Почтовый адрес'}») — "
        "список → создание → редактирование → удаление"
    )
    page = HelpdeskDictPage(admin_page, path, value_field, has_group=has_group)
    page.open(helpdesk_ui_base_url)

    value = _generate_value(key, value_field)
    group_name = _SYSTEM_GROUP_NAME if has_group else None

    with allure.step(f"«Добавить» и заполнить поле, сохранить — запись «{value}» видна в списке"):
        page.create(value, group_name)

    deleted = False
    try:
        new_value = f"{value}_upd"
        with allure.step("Открыть запись на редактирование и изменить значение"):
            row = page.row(value)
            row.locator("a[bp-button='update']").first.click()
            page.wait_loaded()
            page.field(value_field).fill(new_value)
            page.submit_form()

        with allure.step("Изменение сохранилось и видно в списке"):
            assert page.row(new_value).count() > 0, f"Изменённое значение {new_value!r} не видно в списке"

        with allure.step("Удалить запись через иконку-корзину с подтверждением"):
            page.delete(new_value)
            deleted = True

        assert page.row(new_value).count() == 0, "Запись всё ещё видна в списке после удаления"
    finally:
        if not deleted:
            final_row = page.row(new_value) if page.row(new_value).count() > 0 else page.row(value)
            if final_row.count() > 0:
                with allure.step("Teardown: удалить тестовую запись"):
                    final_row.locator("[data-button-type='delete']").first.click()
                    confirm_button = admin_page.get_by_role("button", name=DELETE_CONFIRM_BUTTON_RE)
                    if confirm_button.count() > 0:
                        confirm_button.click()
