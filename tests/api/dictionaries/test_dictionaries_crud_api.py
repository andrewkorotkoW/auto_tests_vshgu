import allure
import pytest

from api.helpers.data_generator import generate_dictionary_payload
from api.helpers.expectations import expect_status

# Типы без дополнительного обязательного meta — POST /dictionaries {name, type} создаёт
# полностью рабочий элемент (project/program_level сюда не входят, см. conftest.py).
SAFE_DICTIONARY_TYPES = ["program_type", "program_department", "learning_format", "tag"]

# Для update отдельно: PATCH /dictionaries/{id} {"name": ...} на элементе type=program_department
# детерминированно отвечает 500 (см. test_update_changes_name ниже) — не входит в общий
# параметр-список update, помечен как xfail-кейс.
UPDATE_SUPPORTED_TYPES = [t for t in SAFE_DICTIONARY_TYPES if t != "program_department"]


@allure.feature("Справочники")
@allure.story("CRUD по типу")
class TestDictionariesCrudApi:

    @allure.title("POST /dictionaries создаёт элемент, он находится через find_by_name")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", SAFE_DICTIONARY_TYPES)
    def test_create_and_find_by_name(self, created_dictionary_item, dictionaries_endpoint, dictionary_type):
        item = created_dictionary_item(dictionary_type=dictionary_type)

        assert isinstance(item["id"], int) and item["id"] > 0
        assert item["type"] == dictionary_type

        found = dictionaries_endpoint.find_by_name(dictionary_type, item["name"])
        assert found is not None, f"Созданный элемент '{item['name']}' не найден по имени"
        assert found["id"] == item["id"]

    @allure.title("GET /dictionaries/by-type/{type} — созданный элемент есть в полном списке типа")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", SAFE_DICTIONARY_TYPES)
    def test_list_by_type_contains_created(self, created_dictionary_item, dictionaries_endpoint, dictionary_type):
        item = created_dictionary_item(dictionary_type=dictionary_type)

        items = dictionaries_endpoint.list_by_type(dictionary_type)
        ids = [i["id"] for i in items]
        assert item["id"] in ids, f"id={item['id']} не найден в list_by_type({dictionary_type})"

    @allure.title("GET /dictionaries?filters[type]&filters[name] — постраничный список фильтруется по типу и имени")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", SAFE_DICTIONARY_TYPES)
    def test_list_paginated_filtered(self, created_dictionary_item, dictionaries_endpoint, dictionary_type):
        item = created_dictionary_item(dictionary_type=dictionary_type)

        items = dictionaries_endpoint.list(dictionary_type=dictionary_type, name=item["name"])
        assert len(items) == 1, f"Фильтр по точному имени должен вернуть 1 элемент, получено {len(items)}"
        assert items[0]["id"] == item["id"]

    @allure.title("PATCH /dictionaries/{id} — обновляет имя, старое имя больше не находится")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", UPDATE_SUPPORTED_TYPES)
    def test_update_changes_name(self, created_dictionary_item, dictionaries_endpoint, dictionary_type):
        item = created_dictionary_item(dictionary_type=dictionary_type)
        new_name = item["name"] + "_upd"

        updated = dictionaries_endpoint.update(item["id"], new_name)
        assert updated["id"] == item["id"]
        assert updated["name"] == new_name

        assert dictionaries_endpoint.find_by_name(dictionary_type, new_name) is not None
        assert dictionaries_endpoint.find_by_name(dictionary_type, item["name"]) is None

    @allure.title("PATCH /dictionaries/{id} для type=program_department — кандидат в дефект (план ждёт 200, факт 500)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Подтверждённый дефект develop: PATCH /dictionaries/{id} {\"name\": ...} на элементе "
            "type=program_department детерминированно отвечает 500 ('\"0\" is not a valid backing "
            "value for enum Dictionaries\\Enums\\DictionaryType', UpdateDictionaryRulesBuilder.php) "
            "— та же 'enum из отсутствующего значения' ошибка, что и у POST без type (см. "
            "test_create_without_type_returns_422), но здесь воспроизводится на штатном PATCH "
            "с валидным телом {\"name\": ...} и только для этого типа справочника; "
            "program_type/learning_format/tag обновляются нормально (см. test_update_changes_name)."
        ),
    )
    def test_update_program_department_name(self, created_dictionary_item, dictionaries_endpoint):
        item = created_dictionary_item(dictionary_type="program_department")
        new_name = item["name"] + "_upd"

        updated = dictionaries_endpoint.update(item["id"], new_name)
        assert updated["name"] == new_name

    @allure.title("DELETE /dictionaries/{id} — элемент перестаёт находиться по имени")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", SAFE_DICTIONARY_TYPES)
    def test_delete_removes_item(self, dictionaries_endpoint, dictionary_type):
        payload = generate_dictionary_payload(dictionary_type=dictionary_type)
        item = dictionaries_endpoint.create(payload["name"], payload["type"])

        assert dictionaries_endpoint.delete(item["id"]) is True
        assert dictionaries_endpoint.find_by_name(dictionary_type, item["name"]) is None

    @allure.title("GET /dictionaries/{id} и PUT /dictionaries/{id} не поддерживаются — 405 (get/update по id не предусмотрены)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_get_and_put_by_id_not_allowed(self, created_dictionary_item, api_client):
        item = created_dictionary_item(dictionary_type="program_type")

        resp_get = api_client.get(f"/dictionaries/{item['id']}")
        expect_status(resp_get, 405)

        resp_put = api_client.put(f"/dictionaries/{item['id']}", json={"name": "x"})
        expect_status(resp_put, 405)
