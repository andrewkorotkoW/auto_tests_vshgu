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

from api.helpers.data_generator import generate_helpdesk_applicant_payload
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


@allure.feature("Хелпдеск: Заявители")
@allure.story("Просмотр карточки заявителя")
@allure.title("UI: карточка заявителя показывает блоки «Информация», «Связанные», «Статистика», «Назначения», «Тикеты»")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_view_applicant_card(admin_page, helpdesk_ui_base_url, helpdesk_endpoint):
    """TC-HELPDESK_APPLICANTS-004. Заявитель — свой auto_test_* (add_applicant через API,
    подтверждено живым прогоном, что создание работает и успешно находится в поиске —
    см. tests/api/helpdesk/test_applicants_api.py::test_create_applicant).

    Teardown здесь НЕТ: у /admin/identity нет маршрута DELETE (docs/helpdesk_recon.md §2,
    уже задокументировано в tests/api/helpdesk/test_applicants_api.py) — созданный
    auto_test_* заявитель остаётся в системе, как и у всех остальных тестов заявителей в
    этом репозитории. Это существующее инфраструктурное ограничение, не новый блокер."""
    payload = generate_helpdesk_applicant_payload()
    with allure.step("Подготовка: создать тестового заявителя через API"):
        resp = helpdesk_endpoint.add_applicant(payload)
        assert resp.status_code < 400, f"Не удалось создать заявителя: {resp.status_code} {resp.text[:300]}"
        found = helpdesk_endpoint.find_applicant_by_email(payload["email"])
        assert found is not None and found["id"], f"Созданный заявитель {payload['email']!r} не найден"
        applicant_id = found["id"]

    page = HelpdeskApplicantsPage(admin_page)
    with allure.step("Открыть карточку заявителя"):
        page.open_show_page(helpdesk_ui_base_url, applicant_id)
        assert f"/admin/identity/{applicant_id}/show" in admin_page.url

    with allure.step("Проверить блоки карточки"):
        body_text = admin_page.locator("body").inner_text()
        for label in (
            "Информация о заявителе",
            "Связанные",
            "Статистика",
            "Назначения",
            "Программы и потоки",
            "Активити",
            "Тикеты",
        ):
            assert label in body_text, f"На карточке заявителя не найден блок «{label}»"

    with allure.step("Блок «Статистика» содержит все 4 показателя"):
        for label in ("Всего тикетов", "Решённых", "В работе", "На уточнении"):
            assert label in body_text, f"В блоке «Статистика» не найден показатель «{label}»"

    with allure.step("Блок «Тикеты» содержит колонки ID/Тема/Статус/Дата создания/Действия"):
        for label in ("ID", "Тема", "Статус", "Дата создания", "Действия"):
            assert label in body_text, f"В блоке «Тикеты» не найдена колонка «{label}»"
