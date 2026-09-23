"""Фикстуры для тестов онбординга (первичный и повторный).

Перенос tests/ui/onboarding/conftest.py коллеги (репозиторий lms, feature/my-tests,
см. report.md разд. 2) — как справочник по составу фикстур, НЕ дословно:
  - fresh_onboarding_user коллеги создаёт пользователя отдельным API-запросом и снимает
    cookie 'develop' из браузера админа (page.context.cookies) — у нас для создания
    пользователя есть API-фикстура created_user (tests/conftest.py) с уникальными
    данными по xdist-воркеру и teardown;
  - согласие на ПД и закрытие onboarding-историй для повторного онбординга сделаны
    через api/helpers/user_prepare_api.prepare_user_for_tests_via_api на нашем
    ApiClient, а не через куки/JSON-файлы на диске (last_used_index.txt и т.п.).

Регион/муниципалитет нигде не хардкодятся литералом в этом модуле: в первичном
онбординге они выбираются в UI как первый доступный вариант в автокомплите
(OnboardingPage.fill_registration_form), а created_user создаёт пользователя с
region_id/municipality_id по умолчанию из api/helpers/data_generator.generate_user_payload
(единственный источник данных о регионах в репозитории — отдельного справочника
регионов, наподобие test_data/regions.py коллеги, у нас нет).
"""
import pytest
from playwright.sync_api import Page, expect

from api.helpers.user_prepare_api import prepare_user_for_tests_via_api
from ui.pages.login_page import LoginPage
from ui.pages.onboarding_page import OnboardingPage

from tests.ui.onboarding.locators import MY_LEARNING_HEADING

@pytest.fixture
def fresh_login_page(page: Page, env, created_user) -> Page:
    """API: создать нового пользователя. UI: войти под ним без авто-прохождения
    онбординга (handle_onboarding=False) — оно является предметом проверки этого модуля,
    в отличие от остальных UI-тестов, где LoginPage.login прокликивает его как шум."""
    user = created_user()
    LoginPage(page).login(
        user["email"], user["password"],
        base_url=env.ui_base_url,
        handle_onboarding=False,
    )
    return page


@pytest.fixture
def primary_onboarded_page(fresh_login_page: Page) -> Page:
    """Проходит первичный онбординг: модалка регион/муниципалитет/согласие →
    «Интерактивное руководство», оставляет пользователя на «Моё обучение»."""
    page = fresh_login_page
    onboarding = OnboardingPage(page)

    onboarding.wait_for_registration_modal()
    onboarding.fill_registration_form()
    onboarding.dismiss_email_opt_out_notice()

    status = onboarding.wait_for_primary_onboarding_or_repeat(timeout=15000)
    assert status == "primary", (
        "Ожидали первичный онбординг для свежесозданного пользователя, "
        f"получили статус: {status}"
    )
    onboarding.remove_tech_banner()
    onboarding.start_onboarding_if_present()
    onboarding.complete_onboarding(max_steps=20)
    expect(page.get_by_role("heading", name=MY_LEARNING_HEADING)).to_be_visible(timeout=15000)
    return page


@pytest.fixture
def repeat_onboarding_page(page: Page, env, created_user) -> Page:
    """API: создать пользователя и сразу закрыть для него первичный онбординг
    (согласие ПД + все onboarding-истории, prepare_user_for_tests_via_api) — в UI
    первичная модалка/тур ему не покажутся, доступен только повторный запуск.
    UI: войти под ним, оставив управление онбордингом тесту (handle_onboarding=False)."""
    user = created_user()
    prepare_user_for_tests_via_api(env, user["email"], user["password"])
    LoginPage(page).login(
        user["email"], user["password"],
        base_url=env.ui_base_url,
        handle_onboarding=False,
    )
    onboarding = OnboardingPage(page)
    # У пользователя, подготовленного через API (без прохождения формы в UI), при
    # логине всё равно показывается тот же диалог «Пожалуйста, заполните...» — но
    # уже без полей региона/муниципалитета, только чекбокс согласия на рекламную
    # рассылку. Это не первичный онбординг (agreement на ПД уже принят через API),
    # это отдельный шаг с тем же диалогом; закрываем его тем же fill_registration_form
    # (он безопасно пропускает отсутствующие поля региона/муниципалитета).
    if onboarding.registration_modal.is_visible(timeout=5000):
        onboarding.fill_registration_form()
    onboarding.dismiss_email_opt_out_notice()
    onboarding.dismiss_cookie_banner()
    onboarding.remove_tech_banner()
    return page
