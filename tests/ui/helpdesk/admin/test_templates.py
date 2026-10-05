"""UI: создание шаблона ответа через форму (/admin/mail-template,
docs/test_cases/helpdesk/templates.md TC-HELPDESK_TEMPLATES-003). Шаблон — свой
Автотест_* (см. api.helpers.data_generator.generate_helpdesk_template_payload). Поле
«Группа» на форме создания опционально (`data-allows-null="true"`, подтверждено по DOM
`/admin/mail-template/create`) — выбор группы в этом тесте не требуется.

ОБНАРУЖЕННЫЙ ДЕФЕКТ (тот же, что в test_groups.py::test_create_group, подтверждён живым
прогоном Playwright headless на develop, НЕ правим — ui/pages/helpdesk_templates_page.py
защищена условиями задачи): `HelpdeskTemplatesPage.fill_create_form()` использует
`page.get_by_label(<подпись>, exact=True)`, но в реальной разметке
`/admin/mail-template/create` подписи («Наименование», «Содержимое», «Ключевые слова») —
обычные `<label>` без `for` и без обёртки вокруг поля, Playwright не может связать
подпись с полем — `get_by_label(...)` находит 0 элементов, `fill_create_form()` падает
по таймауту на первом поле."""
import allure
import pytest

from api.helpers.data_generator import generate_helpdesk_template_payload
from ui.pages.helpdesk_templates_page import HelpdeskTemplatesPage

_LABEL_DEFECT_REASON = (
    "Дефект вёрстки формы /admin/mail-template/create (не в зоне правки — "
    "ui/pages/helpdesk_templates_page.py защищена условиями задачи): подписи полей "
    "(<label>Наименование</label> и т.д.) не связаны с <input>/<textarea> ни через for/id, "
    "ни через обёртку, поэтому page.get_by_label(..., exact=True), который использует "
    "fill_create_form(), стабильно находит 0 элементов. Тот же паттерн, что у групп "
    "(см. test_groups.py). Подтверждено живым прогоном Playwright headless на develop."
)


@allure.feature("Хелпдеск: Шаблоны")
@allure.story("Создание шаблона через форму")
@allure.title("UI: шаблон ответа создаётся через форму «Добавить шаблон ответа» и виден в таблице")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.develop
@pytest.mark.xfail(strict=False, reason=_LABEL_DEFECT_REASON)
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
