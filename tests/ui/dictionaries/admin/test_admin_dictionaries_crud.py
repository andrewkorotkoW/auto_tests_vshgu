"""UI: админка → «Справочники» → «Вид программы» (program_type) — CRUD через форму.

Раздел покрыт в UI впервые (см. ui/pages/admin_dictionaries_page.py); API-round-trip уже
покрыт tests/api/dictionaries. program_type выбран как единственный тип, для которого
CRUD безопасен без побочных эффектов (см. docstring conftest.py::DICTIONARY_TYPE).

Каждый тест перезагружает страницу после мутации и проверяет список заново — вместо того
чтобы доверять только DOM, оставшемуся в памяти страницы после клика (тот же приём, что и
проверка персистентности повторным GET на API-уровне)."""
import allure
import pytest


@allure.feature("Справочники UI")
@allure.story("Админка — CRUD «Вид программы»")
@pytest.mark.ui
@pytest.mark.dictionaries
class TestAdminDictionariesCrud:

    @allure.title("Созданный элемент справочника отображается в таблице и переживает перезагрузку страницы")
    def test_create_item_persists_after_reload(
        self, env, admin_dictionaries_page, dictionary_type, dictionary_name, cleanup_dictionary_items
    ):
        name = dictionary_name()
        cleanup_dictionary_items(name)

        with allure.step(f"Создать элемент '{name}' через модалку «Добавить»"):
            admin_dictionaries_page.create_item(name)

        with allure.step("Перезагрузить страницу и убедиться, что элемент сохранился"):
            admin_dictionaries_page.open(env.ui_base_url, dictionary_type)
            assert name in admin_dictionaries_page.values()

    @allure.title("Редактирование переименовывает элемент, новое имя переживает перезагрузку")
    def test_edit_item_renames_and_persists(
        self, env, admin_dictionaries_page, dictionary_type, dictionary_name, cleanup_dictionary_items
    ):
        name = dictionary_name("исходное_")
        new_name = dictionary_name("переименовано_")
        cleanup_dictionary_items(name)
        cleanup_dictionary_items(new_name)

        with allure.step(f"Создать элемент '{name}'"):
            admin_dictionaries_page.create_item(name)

        with allure.step(f"Переименовать в '{new_name}'"):
            admin_dictionaries_page.edit_item(name, new_name)
            assert admin_dictionaries_page.row(name).count() == 0

        with allure.step("Перезагрузить страницу и убедиться, что новое имя сохранилось, а старое пропало"):
            admin_dictionaries_page.open(env.ui_base_url, dictionary_type)
            values = admin_dictionaries_page.values()
            assert new_name in values
            assert name not in values

    @allure.title("Удаление убирает элемент из таблицы и он не возвращается после перезагрузки")
    def test_delete_item_removes_and_stays_gone(
        self, env, admin_dictionaries_page, dictionary_type, dictionary_name, cleanup_dictionary_items
    ):
        name = dictionary_name()
        cleanup_dictionary_items(name)  # страховка на случай, если delete_item ниже не сработает

        with allure.step(f"Создать элемент '{name}'"):
            admin_dictionaries_page.create_item(name)

        with allure.step("Удалить его через модалку подтверждения"):
            admin_dictionaries_page.delete_item(name)

        with allure.step("Перезагрузить страницу и убедиться, что элемент не вернулся"):
            admin_dictionaries_page.open(env.ui_base_url, dictionary_type)
            assert name not in admin_dictionaries_page.values()
