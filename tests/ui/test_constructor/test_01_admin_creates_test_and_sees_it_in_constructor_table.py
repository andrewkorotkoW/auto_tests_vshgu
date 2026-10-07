"""Админка → «Конструктор тестов и опросов»: админ создаёт тест через мастер
создания и видит его в таблице конструктора.

Перенос test_01_admin_creates_test_and_sees_it_in_constructor_table.py коллеги
(origin/feature/test-constructor-autotests) на нашу архитектуру: Page Object
(ConstructorAdminPage) вместо локаторов в тесте, teardown через
TestsEndpoint.mass_delete вместо cleanup_manager. Строка в таблице ищется прямым
локатором по тексту (без вызова search_by_name) — поиск по имени в таблице
конструктора не работает (известный баг стенда, см. докстринг
ConstructorAdminPage), но новый тест и без поиска виден в таблице: список
отсортирован по created_at desc, свежесозданная запись — первая (проверено
GET /tests?per-page=25 в разведке перед написанием теста).
"""
import allure
import pytest

from api.helpers.data_generator import unique_suffix


@allure.feature("Конструктор тестов и опросов UI")
@allure.story("Админка: создание теста")
class TestAdminCreatesTestAndSeesItInConstructorTable:

    @allure.title("UI: Администратор создаёт тест и видит его в таблице конструктора")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.ui
    @pytest.mark.test_constructor
    def test_admin_creates_test_and_sees_it_in_constructor_table(
        self, constructor_admin_page, env, register_constructor_test
    ):
        constructor_name = f"Автотест_КонструкторТест_{unique_suffix()}"
        topic = "AQA constructor topic"

        with allure.step("1. Открыть форму создания и создать тест"):
            constructor_admin_page.open_create_page(env.ui_base_url)
            constructor_admin_page.create_test_on_first_step(
                admin_name=constructor_name,
                external_name=constructor_name,
                topic=topic,
            )
            content_id = constructor_admin_page.get_current_constructor_id()
            register_constructor_test(content_id)
            constructor_admin_page.assert_created_test_constructor_opened()

        with allure.step("2. Открыть таблицу конструктора и убедиться, что тест виден"):
            constructor_admin_page.open_constructor_table(env.ui_base_url)
            constructor_admin_page.assert_constructor_row_visible(
                constructor_name=constructor_name,
                constructor_type="Тест",
                topic=topic,
            )
