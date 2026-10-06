"""UI: создание шаблона ответа через форму (/admin/mail-template,
docs/test_cases/helpdesk/templates.md TC-HELPDESK_TEMPLATES-003). Шаблон — свой
Автотест_* (см. api.helpers.data_generator.generate_helpdesk_template_payload). Поле
«Группа» на форме создания опционально (`data-allows-null="true"`, подтверждено по DOM
`/admin/mail-template/create`) — выбор группы в этом тесте не требуется.

Исходный дефект (тот же, что был у групп — labels без for/id, get_by_label не находил
поля) исправлен в ui/pages/helpdesk_templates_page.py задачей t1: fill_create_form()
переведён на локатор по bp-field-name, «Содержимое» заполняется через Quill
contenteditable (.ql-editor), а не textarea."""
import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_template_payload
from ui.pages.helpdesk_templates_page import HelpdeskTemplatesPage


@allure.feature("Хелпдеск: Шаблоны")
@allure.story("Создание шаблона через форму")
@allure.title("UI: шаблон ответа создаётся через форму «Добавить шаблон ответа» и виден в таблице")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
def test_create_template(admin_page, helpdesk_ui_base_url):
    page = HelpdeskTemplatesPage(admin_page)
    page.open(helpdesk_ui_base_url)
    payload = generate_helpdesk_template_payload()

    try:
        with allure.step("Заполнить форму «Добавить шаблон ответа» и сохранить"):
            page.create_template(payload)
    finally:
        if page.row(payload["name"]).count() > 0:
            with allure.step("Teardown: удалить созданный тестовый шаблон"):
                page.delete_template(payload["name"])
