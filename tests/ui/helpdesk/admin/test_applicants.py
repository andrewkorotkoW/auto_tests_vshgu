"""UI: переход из карточки заявителя в карточку пользователя ВШГУ, вкладка «Обучение»
(docs/test_cases/helpdesk/applicants.md TC-HELPDESK_APPLICANTS-008). Нужен заявитель с
реально назначенным потоком обучения — такие данные не создаются автоматизацией (учебный
домен вне скоупа, см. APPLICANTS-006/007 в том же файле), поэтому ищем существующего
подходящего заявителя только чтением (fixture applicant_with_education_stream,
tests/ui/helpdesk/admin/conftest.py) — его данные не мутируем.

ОБНАРУЖЕННЫЙ ДЕФЕКТ (подтверждён живым прогоном Playwright headless на develop против
реального заявителя с назначенным потоком, НЕ правим — ui/pages/helpdesk_applicants_page.py
защищена условиями задачи): кнопка «Управление обучением» в реальной разметке — это
`<a href="https://global-develop.d2.devspark.ru/admin/users/{id}/assigment/education"
target="_blank" class="btn ...">`, то есть ссылка, открывающая НОВУЮ вкладку браузера, а
не кнопка. `HelpdeskApplicantsPage.go_to_vshgu_user_education()` ищет её через
`page.get_by_role("button", name="Управление обучением")` — у ссылки `<a>` без
`role="button"` вычисляемая ARIA-роль "link", а не "button", поэтому локатор находит 0
элементов (подтверждено: `get_by_role("link", ...)` находит 2 совпадения на той же
странице, `get_by_role("button", ...)` — 0). Даже если бы роль совпала, `target="_blank"`
означает переход в новую вкладку/страницу Playwright, а не навигацию в текущей, которую
ждёт `expect_navigation()` внутри метода."""
import allure
import pytest

from ui.pages.helpdesk_applicants_page import HelpdeskApplicantsPage

_BUTTON_ROLE_DEFECT_REASON = (
    "Дефект page-объекта/разметки (не в зоне правки — ui/pages/helpdesk_applicants_page.py "
    "защищена условиями задачи): кнопка «Управление обучением» в реальной разметке — это "
    "<a href=\"...\" target=\"_blank\">, а не <button>. go_to_vshgu_user_education() ищет её "
    "через get_by_role(\"button\", ...), который находит 0 элементов (подтверждено: "
    "get_by_role(\"link\", ...) находит 2 совпадения на той же странице). Переход, кроме "
    "того, открывается в новой вкладке (target=_blank), а не навигацией в текущей, которую "
    "ждёт expect_navigation() внутри метода."
)


@allure.feature("Хелпдеск: Заявители")
@allure.story("Переход в карточку пользователя (вкладка «Обучение»)")
@allure.title("UI: кнопка «Управление обучением» открывает карточку пользователя ВШГУ на вкладке «Обучение»")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
@pytest.mark.xfail(strict=False, reason=_BUTTON_ROLE_DEFECT_REASON)
def test_navigate_to_user_education_tab(admin_page, helpdesk_ui_base_url, applicant_with_education_stream):
    if applicant_with_education_stream is None:
        pytest.xfail(
            "На develop не нашлось ни одного заявителя с реально назначенным потоком "
            "обучения среди первой страницы каталога (/admin/identity/search) — такие "
            "данные не создаются автоматизацией (учебный домен вне скоупа, см. "
            "APPLICANTS-006/007 в docs/test_cases/helpdesk/applicants.md)."
        )

    page = HelpdeskApplicantsPage(admin_page)

    with allure.step("Открыть карточку заявителя с назначенным потоком обучения"):
        page.open_show_page(helpdesk_ui_base_url, applicant_with_education_stream)

    with allure.step("Кликнуть «Управление обучением» — открывается карточка пользователя ВШГУ"):
        page.go_to_vshgu_user_education()

    assert "global-develop.d2.devspark.ru" in admin_page.url
    assert "/assigment/education" in admin_page.url
