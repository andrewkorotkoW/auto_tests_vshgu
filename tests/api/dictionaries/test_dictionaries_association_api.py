import allure
import pytest

from api.helpers.data_generator import generate_dictionary_payload, generate_stream_payload


@allure.feature("Справочники")
@allure.story("Связь с программами и пользователями")
class TestDictionariesAssociationApi:

    @allure.title("Поток программы, созданный со ссылкой на новый элемент справочника program_type, хранит эту связь")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_stream_created_with_new_dictionary_item_persists_reference(
        self, created_dictionary_item, created_program, streams_endpoint, api_client
    ):
        item = created_dictionary_item(dictionary_type="program_type")
        program = created_program()

        stream_payload = generate_stream_payload(program_type=item["id"])
        resp = api_client.post(f"/programs/{program['id']}/streams", json=stream_payload)
        assert resp.status_code in (200, 201), f"Не удалось создать поток: {resp.status_code} {resp.text}"
        stream_id = resp.json()["data"]["id"]

        with allure.step("Связь сохраняется и после повторного GET потока"):
            fetched = streams_endpoint.get(program["id"], stream_id)
            program_type_ref = fetched["attributes"]["program_type"]
            assert program_type_ref is not None, "Поток не хранит ссылку на элемент справочника program_type"
            assert program_type_ref["id"] == item["id"]
            assert program_type_ref["name"] == item["name"]

    @allure.title("Пользователь, созданный со ссылкой на существующие region/municipality, хранит эту связь")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_user_created_with_dictionary_region_persists_reference(self, created_user, users_endpoint, dictionaries_endpoint):
        """region/municipality — read-only справочники ФИАС на develop (мишн-док), поэтому
        связь проверяется на уже существующих элементах (region_id=1/municipality_id=158 —
        значения по умолчанию generate_user_payload), а не на созданных тестом записях."""
        user = created_user()

        fetched = users_endpoint.get(user["id"])
        region = fetched["attributes"]["region"]
        municipality = fetched["attributes"]["municipality"]
        assert region is not None, "У пользователя не сохранилась связь с элементом справочника region"
        assert municipality is not None, "У пользователя не сохранилась связь с элементом справочника municipality"

        region_dictionary_items = dictionaries_endpoint.list_by_type("region")
        region_item = next((i for i in region_dictionary_items if i["id"] == region["dictionary_id"]), None)
        assert region_item is not None, f"dictionary_id={region['dictionary_id']} региона не найден в справочнике region"
        assert region_item["name"] == region["region_name"]
