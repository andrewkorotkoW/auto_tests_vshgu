import allure
import pytest

from api.helpers.data_generator import generate_dictionary_payload
from api.helpers.expectations import expect_status
from utils.logger import logger


@allure.feature("Справочники")
@allure.story("Негативные сценарии и права доступа")
class TestDictionariesNegativeApi:

    @allure.title("POST /dictionaries с пустым name — 422")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_create_empty_name_returns_422(self, api_client):
        resp = api_client.post("/dictionaries", json={"name": "", "type": "program_type"})
        expect_status(resp, 422)
        assert "name" in resp.json().get("errors", {})

    @allure.title("POST /dictionaries без поля type — кандидат в дефект (план ждёт 422, факт 500)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Кандидат в дефект (docs/plans/2026-09-25_dictionaries_mission.md): POST /dictionaries "
            "без поля type отвечает 500 ('\"0\" is not a valid backing value for enum "
            "Dictionaries\\Enums\\DictionaryType') вместо ожидаемой валидационной 422 — сервер "
            "падает на приведении отсутствующего значения к enum до валидации."
        ),
    )
    def test_create_without_type_returns_422(self, api_client):
        payload = generate_dictionary_payload()
        resp = api_client.post("/dictionaries", json={"name": payload["name"]})
        assert resp.status_code == 422, f"Ожидали 422, получили {resp.status_code}: {resp.text}"

    @allure.title("POST /dictionaries от обычного пользователя — 403 (раздел админский)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_create_forbidden_for_regular_user(self, second_user_dictionaries_endpoint):
        payload = generate_dictionary_payload()
        resp = second_user_dictionaries_endpoint.client.post(
            "/dictionaries", json={"name": payload["name"], "type": payload["type"]}
        )
        assert resp.status_code == 403, f"Ожидали 403, получили {resp.status_code}: {resp.text}"

    @allure.title("GET /dictionaries/by-type/{type} от обычного пользователя — доступно (раздел на чтение открыт всем)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    def test_list_by_type_allowed_for_regular_user(self, second_user_dictionaries_endpoint):
        """Не дефект, а документирование фактической модели прав: в отличие от
        /notifications/* (403 целиком для не-админов, README §13), справочники читаются
        любым авторизованным пользователем — POST/PATCH/DELETE админские, GET нет."""
        items = second_user_dictionaries_endpoint.list_by_type("program_type")
        assert isinstance(items, list) and len(items) > 0

    @allure.title(
        "POST /dictionaries type=project/program_level без meta.experts_entity_id ломает "
        "GET по всему типу — подтверждённый дефект"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    @pytest.mark.dictionaries
    @pytest.mark.parametrize("dictionary_type", ["project", "program_level"])
    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Подтверждённый дефект develop: для type=project/program_level в БД дополнительно "
            "хранится meta.experts_entity_id (см. мишн-док), но POST /dictionaries {name, type} "
            "не требует и не валидирует это поле — создание проходит (201). После этого "
            "GET /dictionaries/by-type/{type} (и постраничный GET /dictionaries?filters[type]=...) "
            "отвечают 500 'Undefined array key \"experts_entity_id\"' "
            "(Dictionaries/Models/Casts/Meta/ExpertsDictionaryMeta.php) для ЛЮБОГО пользователя, "
            "пока сломанный элемент не будет удалён напрямую по id — воспроизведено и "
            "самостоятельно устранено вручную во время разведки к этой задаче."
        ),
    )
    def test_create_experts_type_without_meta_breaks_type_reads(self, dictionaries_endpoint, api_client, dictionary_type):
        payload = generate_dictionary_payload(dictionary_type=dictionary_type)
        item = dictionaries_endpoint.create(payload["name"], payload["type"])
        try:
            resp = api_client.get(
                f"/dictionaries/by-type/{dictionary_type}"
                "?sort[0][name]=dictionary.name&sort[0][direction]=asc"
            )
            assert resp.status_code == 200, (
                f"Создание элемента type={dictionary_type} без meta.experts_entity_id (id={item['id']}) "
                f"сломало чтение всего типа: {resp.status_code} {resp.text[:300]}"
            )
        finally:
            dictionaries_endpoint.delete(item["id"])
            recovery = api_client.get(
                f"/dictionaries/by-type/{dictionary_type}"
                "?sort[0][name]=dictionary.name&sort[0][direction]=asc"
            )
            if recovery.status_code != 200:
                logger.error(
                    f"КРИТИЧНО: удаление сломанного элемента {item['id']} (type={dictionary_type}) "
                    f"не восстановило GET by-type: {recovery.status_code} {recovery.text[:300]}"
                )
