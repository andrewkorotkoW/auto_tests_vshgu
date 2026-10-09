"""Граничные и ошибочные случаи для /ratings* (docs/qr_code_ratings_recon.md,
раздел «Рейтинги/отзывы»): анонимный доступ, отсутствующие поля, несуществующие
сущности, невалидный/непригодный entity_type."""
import allure
import pytest

ENTITY_TYPE_KB_MATERIAL = "knowledge_base_material"


@allure.feature("Рейтинги и отзывы")
@allure.story("Негативные и граничные сценарии")
@pytest.mark.api
class TestRatingsNegative:

    @allure.title("GET /ratings анонимно → 401")
    def test_list_ratings_anon_401(self, anon_api_client):
        resp = anon_api_client.get("/ratings")
        assert resp.status_code == 401

    @allure.title("GET/DELETE /ratings/my-review без entity_type/entity_id → 422")
    @pytest.mark.parametrize("method", ["get", "delete"])
    @pytest.mark.parametrize("params", ["", "?entity_type=knowledge_base_material", "?entity_id=1"])
    def test_my_review_missing_params_422(self, api_client, method, params):
        resp = getattr(api_client, method)(f"/ratings/my-review{params}")
        assert resp.status_code == 422
        errors = resp.json().get("errors", {})
        assert errors, resp.text

    @allure.title("GET/DELETE /ratings/my-review анонимно → 401")
    @pytest.mark.parametrize("method", ["get", "delete"])
    def test_my_review_anon_401(self, anon_api_client, method):
        resp = getattr(anon_api_client, method)(
            f"/ratings/my-review?entity_type={ENTITY_TYPE_KB_MATERIAL}&entity_id=1"
        )
        assert resp.status_code == 401

    @allure.title("GET /ratings/my-review для несуществующей сущности → 404")
    def test_my_review_for_nonexistent_entity_404(self, api_client):
        resp = api_client.get(f"/ratings/my-review?entity_type={ENTITY_TYPE_KB_MATERIAL}&entity_id=999999999")
        assert resp.status_code == 404

    @allure.title("GET /ratings/my-review для реальной сущности без моего отзыва → 200 с пустыми данными")
    def test_my_review_for_real_entity_without_my_review_returns_empty(
        self, api_client, created_course
    ):
        material = created_course()
        resp = api_client.get(f"/ratings/my-review?entity_type={ENTITY_TYPE_KB_MATERIAL}&entity_id={material['id']}")
        assert resp.status_code == 200
        assert not resp.json().get("data")

    @allure.title("DELETE /ratings/my-review без активного отзыва — известный дефект (500 вместо 404)")
    @pytest.mark.xfail(
        strict=False,
        reason="Известный дефект: DELETE /ratings/my-review для реально существующей "
        "сущности, у которой нет моего отзыва (ещё не создавался или уже удалён), "
        "отвечает 500 ('Call to a member function delete() on null', "
        "RatingController.php:81) вместо ожидаемых 404/200 — контроллер не проверяет, "
        "что отзыв найден, перед вызовом delete() на нём.",
    )
    def test_delete_my_review_without_active_review_is_not_500(self, api_client, created_course):
        material = created_course()
        resp = api_client.delete(
            f"/ratings/my-review?entity_type={ENTITY_TYPE_KB_MATERIAL}&entity_id={material['id']}"
        )
        assert resp.status_code in (200, 404), resp.text

    @allure.title("POST /ratings без обязательных полей конверта → 422")
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"data": {}},
            {"data": {"attributes": {}}},
            {"rating": 5, "entity_type": ENTITY_TYPE_KB_MATERIAL, "entity_id": 1},
        ],
    )
    def test_create_rating_missing_fields_422(self, api_client, payload):
        resp = api_client.post("/ratings", json=payload)
        assert resp.status_code == 422
        errors = resp.json().get("errors", {})
        assert "data.attributes.rating" in errors
        assert "data.attributes.entity_type" in errors
        assert "data.attributes.entity_id" in errors

    @allure.title("POST /ratings с неизвестным entity_type → 404 'Неверный alias сущности'")
    def test_create_rating_unknown_entity_type_404(self, api_client):
        resp = api_client.post(
            "/ratings",
            json={"data": {"attributes": {"rating": 5, "entity_type": "not-a-real-type", "entity_id": 1}}},
        )
        assert resp.status_code == 404
        assert "alias" in resp.json().get("data", {}).get("error", "").lower()

    @allure.title("POST /ratings на несуществующий материал известного типа → 404")
    def test_create_rating_nonexistent_entity_id_404(self, api_client):
        resp = api_client.post(
            "/ratings",
            json={
                "data": {
                    "attributes": {
                        "rating": 5,
                        "entity_type": ENTITY_TYPE_KB_MATERIAL,
                        "entity_id": 999999999,
                    }
                }
            },
        )
        assert resp.status_code == 404

    @allure.title("GET /ratings/<несуществующий id> → 404")
    def test_get_rating_nonexistent_404(self, api_client):
        resp = api_client.get("/ratings/999999999")
        assert resp.status_code == 404
