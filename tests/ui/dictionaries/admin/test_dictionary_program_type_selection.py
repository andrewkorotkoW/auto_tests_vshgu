"""UI: элемент справочника program_type, созданный в «Справочники», доступен для выбора
в селекте «Вид программы» формы создания потока программы.

AdminProgramsPage.select_program_type_value(value) (в отличие от select_program_type(),
который берёт первый попавшийся пункт) допечатывает точное имя и выбирает именно его —
метод, добавленный специально под такую проверку связи справочника с формой (см. его
докстринг в ui/pages/admin_programs_page.py и мишн-док
docs/plans/2026-09-25_dictionaries_mission.md)."""
import datetime as dt

import allure
import pytest

from api.helpers.data_generator import generate_program_payload, unique_suffix
from ui.pages.admin_programs_page import AdminProgramsPage
from ui.pages.user_sidebar_page import UserSidebarPage


@allure.feature("Справочники UI")
@allure.story("Связь с формой потока программы")
@pytest.mark.ui
@pytest.mark.dictionaries
class TestDictionaryProgramTypeSelection:

    @allure.title("Новый элемент справочника «Вид программы» можно выбрать в форме создания потока")
    def test_new_program_type_selectable_in_stream_form(
        self,
        admin_page,
        env,
        programs_endpoint,
        admin_dictionaries_page,
        dictionary_name,
        cleanup_dictionary_items,
    ):
        name = dictionary_name()
        cleanup_dictionary_items(name)

        with allure.step(f"Создать элемент справочника '{name}' в «Справочники» → «Вид программы»"):
            admin_dictionaries_page.create_item(name)

        with allure.step("Создать программу (через API — сама программа не предмет проверки)"):
            program = programs_endpoint.create(generate_program_payload())
            program_id = program["id"]

        try:
            with allure.step("Открыть форму создания потока программы"):
                admin_page.goto(f"{env.ui_base_url}/admin/programs/{program_id}")
                UserSidebarPage(admin_page).dismiss_popups()
                programs_page = AdminProgramsPage(admin_page)
                programs_page.open_create_stream_form()

            today = dt.date.today()
            date_from = today.strftime("%d.%m.%Y")
            date_to = (today + dt.timedelta(days=30)).strftime("%d.%m.%Y")

            with allure.step("Заполнить обязательные поля потока"):
                programs_page.fill_stream_basic_fields(
                    name=f"Автотест поток {unique_suffix()}",
                    place="Москва",
                    date_from=date_from,
                    date_to=date_to,
                )
                programs_page.add_manager()
                programs_page.add_external_manager()
                programs_page.select_project()
                programs_page.select_academic_director()
                programs_page.select_cost_program_group()
                programs_page.select_unit()

            with allure.step(f"Выбрать созданный элемент справочника '{name}' в поле «Вид программы»"):
                programs_page.select_program_type_value(name)

            with allure.step("Сохранить поток"):
                programs_page.select_program_form()
                programs_page.fill_total_load()
                programs_page.save_stream()
        finally:
            with allure.step("Удалить программу (каскадно поток)"):
                programs_endpoint.mass_delete([program_id])
