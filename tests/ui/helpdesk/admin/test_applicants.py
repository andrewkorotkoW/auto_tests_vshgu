"""UI: переход из карточки заявителя в карточку пользователя ВШГУ, вкладка «Обучение»
(docs/test_cases/helpdesk/applicants.md TC-HELPDESK_APPLICANTS-008). Нужен заявитель с
реально назначенным потоком обучения — такие данные не создаются автоматизацией (учебный
домен вне скоупа, см. APPLICANTS-006/007 в том же файле), поэтому ищем существующего
подходящего заявителя только чтением (fixture applicant_with_education_stream,
tests/ui/helpdesk/admin/conftest.py, перебирает всех заявителей постранично) — его данные
не мутируем.

Исходный дефект (кнопка искалась через get_by_role("button", ...) вместо "link", переход
ждался в текущей вкладке вместо новой) исправлен в ui/pages/helpdesk_applicants_page.py
задачей t1: go_to_vshgu_user_education() теперь ищет ссылку через get_by_role("link", ...)
и возвращает Playwright Page новой вкладки (target=_blank) — именно её URL нужно проверять,
а не URL исходной admin_page (она остаётся на /admin/identity/{id}/show)."""
import allure
import pytest

from ui.pages.helpdesk_applicants_page import HelpdeskApplicantsPage


@allure.feature("Хелпдеск: Заявители")
@allure.story("Переход в карточку пользователя (вкладка «Обучение»)")
@allure.title("UI: кнопка «Управление обучением» открывает карточку пользователя ВШГУ на вкладке «Обучение»")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_navigate_to_user_education_tab(admin_page, helpdesk_ui_base_url, applicant_with_education_stream):
    if applicant_with_education_stream is None:
        pytest.xfail(
            "На develop не нашлось ни одного заявителя с реально назначенным потоком "
            "обучения — такие данные не создаются автоматизацией (учебный домен вне скоупа, "
            "см. APPLICANTS-006/007 в docs/test_cases/helpdesk/applicants.md)."
        )

    page = HelpdeskApplicantsPage(admin_page)

    with allure.step("Открыть карточку заявителя с назначенным потоком обучения"):
        page.open_show_page(helpdesk_ui_base_url, applicant_with_education_stream)

    with allure.step("Кликнуть «Управление обучением» — открывается карточка пользователя ВШГУ в новой вкладке"):
        new_page = page.go_to_vshgu_user_education()

    assert "global-develop.d2.devspark.ru" in new_page.url
    assert "/assigment/education" in new_page.url
    new_page.close()
