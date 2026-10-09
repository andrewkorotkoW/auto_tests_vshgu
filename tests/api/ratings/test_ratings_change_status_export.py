"""POST /ratings/change-status, POST /ratings/export (docs/qr_code_ratings_recon.md,
раздел «Рейтинги/отзывы»)."""
import allure
import pytest

ENTITY_TYPE_KB_MATERIAL = "knowledge_base_material"


@allure.feature("Рейтинги и отзывы")
@allure.story("Модерация (change-status) и экспорт")
@pytest.mark.api
class TestRatingsChangeStatusExport:

    @allure.title("Admin меняет статус отзыва на допустимые целые 0/1/2")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("status", [1, 2, 0])
    def test_change_status_admin_accepts_int_values(
        self, ratings_endpoint, created_course, created_rating, status
    ):
        """Допустимые значения status эмпирически подобраны при подготовке задачи: это
        целые числа 0/1/2 (совпадают со значениями status в GET /ratings) — строковые
        "approved"/"rejected"/"pending" отвергаются валидатором (см. тест ниже)."""
        material = created_course()
        rating_data = created_rating(
            rating=3, entity_type=ENTITY_TYPE_KB_MATERIAL, entity_id=material["id"]
        )
        result = ratings_endpoint.change_rating_status([rating_data["id"]], status)
        assert result["data"]["status"] == "success"

        fetched = ratings_endpoint.get_rating(rating_data["id"])
        assert fetched["status"] == status

    @allure.title("Admin: пустое тело change-status → 422 с обязательными review_ids/status")
    def test_change_status_missing_fields_422(self, api_client):
        resp = api_client.post("/ratings/change-status", json={})
        assert resp.status_code == 422
        errors = resp.json().get("errors", {})
        assert "data.attributes.review_ids" in errors
        assert "data.attributes.status" in errors

    @allure.title("Строковый статус отвергается — требуется целое число")
    def test_change_status_rejects_non_integer_status(self, ratings_endpoint, created_course, created_rating):
        material = created_course()
        rating_data = created_rating(
            rating=3, entity_type=ENTITY_TYPE_KB_MATERIAL, entity_id=material["id"]
        )
        resp = ratings_endpoint.client.post(
            "/ratings/change-status",
            json={"data": {"attributes": {"review_ids": [rating_data["id"]], "status": "approved"}}},
        )
        assert resp.status_code == 422
        assert "data.attributes.status" in resp.json().get("errors", {})

    @allure.title("Обычный слушатель не может менять статус отзыва → 403")
    def test_change_status_forbidden_for_regular_user(
        self, created_course, second_user_ratings_endpoint, created_rating
    ):
        material = created_course()
        _user, listener_ratings = second_user_ratings_endpoint()
        rating_data = created_rating(
            endpoint=listener_ratings, rating=3, entity_type=ENTITY_TYPE_KB_MATERIAL, entity_id=material["id"]
        )

        resp = listener_ratings.client.post(
            "/ratings/change-status",
            json={"data": {"attributes": {"review_ids": [rating_data["id"]], "status": 2}}},
        )
        assert resp.status_code == 403

    @allure.title("POST /ratings/export → 200 result=ok для admin и для обычного пользователя")
    def test_export_returns_ok_regardless_of_role(self, ratings_endpoint, second_user_ratings_endpoint):
        """Контракт ответа подтверждён разведкой (docs/qr_code_ratings_recon.md): синхронный
        200 без обязательных полей. Реальный побочный эффект (письмо/файл/ссылка) этим тестом
        НЕ проверяется — разведка явно предупреждает не фиксировать его как «одинаковый для
        всех ролей» без проверки факта; здесь проверяется только контракт ответа API."""
        admin_result = ratings_endpoint.export_ratings()
        assert admin_result == {"result": "ok"}

        _user, listener_ratings = second_user_ratings_endpoint()
        listener_result = listener_ratings.export_ratings()
        assert listener_result == {"result": "ok"}

    @allure.title("Анонимный запрос export → 401")
    def test_export_anon_401(self, anon_api_client):
        resp = anon_api_client.post("/ratings/export", json={})
        assert resp.status_code == 401
