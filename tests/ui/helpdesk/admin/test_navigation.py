"""UI: навигация по разделам админки хелпдеска (helpdesk-develop.d2.devspark.ru,
Laravel Backpack, отдельный домен от остальной Vue-админки портала).

Переход — прямой навигацией (SomeHelpdeskPage.open(base_url)), а не кликом по боковому
меню (admin_page уже авторизована общей кукой .d2.devspark.ru, см. conftest.py). `<title>`
не всегда обновляется при прямой навигации (docs/helpdesk_recon.md) — проверяем видимый
h1/контент раздела, а не page.title().

Проверка таблицы — через общий `table.dataTable`, а не `HelpdeskAdminPage.table`
(`#crudTable`, ui/pages/helpdesk_base_page.py, не правим): на /admin/group, /admin/user,
/admin/ticket, /admin/identity реальный id таблицы — с динамическим хеш-суффиксом
(`crudTable_<hash>`, подтверждено живым прогоном), статический `#crudTable` есть только
на /admin/mail-template. Из-за этого `.table`/`.row()`/`delete_row()` не находят таблицу
на 4 из 5 разделов со списком — отдельный найденный дефект, см. итоговый отчёт."""
import allure
import pytest
from playwright.sync_api import expect

from ui.pages.helpdesk_applicants_page import HelpdeskApplicantsPage
from ui.pages.helpdesk_dashboards_page import HelpdeskDashboardsPage
from ui.pages.helpdesk_groups_page import HelpdeskGroupsPage
from ui.pages.helpdesk_templates_page import HelpdeskTemplatesPage
from ui.pages.helpdesk_tickets_page import HelpdeskTicketsPage
from ui.pages.helpdesk_users_page import HelpdeskUsersPage


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Обращения» (тикеты)")
@allure.title("UI: переход на страницу тикетов открывает таблицу обращений")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_tickets_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskTicketsPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskTicketsPage.PATH}")
    expect(admin_page.locator("h1")).to_have_text("Обращения пользователей")
    expect(admin_page.locator("table.dataTable").first).to_be_visible()


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Системные группы»")
@allure.title("UI: переход на страницу групп открывает таблицу системных групп")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_groups_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskGroupsPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskGroupsPage.PATH}")
    expect(admin_page.locator("h1")).to_have_text("Системные группы")
    expect(admin_page.locator("table.dataTable").first).to_be_visible()


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Список системных пользователей»")
@allure.title("UI: переход на страницу пользователей открывает таблицу пользователей")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_users_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskUsersPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskUsersPage.PATH}")
    expect(admin_page.locator("h1")).to_have_text("Список системных пользователей")
    expect(admin_page.locator("table.dataTable").first).to_be_visible()


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Каталог заявителей»")
@allure.title("UI: переход на страницу заявителей открывает каталог заявителей")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_applicants_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskApplicantsPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskApplicantsPage.PATH}")
    expect(admin_page.locator("h1")).to_have_text("Каталог заявителей")
    expect(admin_page.locator("table.dataTable").first).to_be_visible()


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Шаблоны ответов»")
@allure.title("UI: переход на страницу шаблонов открывает список шаблонов ответов")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_templates_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskTemplatesPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskTemplatesPage.PATH}")
    expect(admin_page.locator("h1")).to_have_text("Шаблоны ответов")
    expect(admin_page.locator("table.dataTable").first).to_be_visible()


@allure.feature("Хелпдеск: навигация")
@allure.story("Переход на «Дашборды»")
@allure.title("UI: переход на страницу дашбордов отрисовывает графики")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.develop
def test_dashboards_section(admin_page, helpdesk_ui_base_url):
    page = HelpdeskDashboardsPage(admin_page)
    page.open(helpdesk_ui_base_url)

    expect(admin_page).to_have_url(f"{helpdesk_ui_base_url}{HelpdeskDashboardsPage.PATH}")
    # На странице нет <h1> (докстринг HelpdeskDashboardsPage) — виден активный пункт
    # бокового меню «Дашборды» и хотя бы один отрисованный график Highcharts.
    expect(admin_page.get_by_text("Дашборды", exact=True).first).to_be_visible()
    expect(admin_page.locator(".highcharts-container").first).to_be_visible()
