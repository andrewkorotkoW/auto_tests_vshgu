"""POST/GET /ratings, GET/DELETE /ratings/my-review (docs/qr_code_ratings_recon.md,
раздел «Рейтинги/отзывы») — полный цикл отзыва на tincan-курс, обёрнутый материалом
базы знаний (entity_type="knowledge_base_material", см. conftest.py этого пакета)."""
import allure
import pytest

ENTITY_TYPE_KB_MATERIAL = "knowledge_base_material"


@allure.feature("Рейтинги и отзывы")
@allure.story("Полный цикл отзыва на курс")
@pytest.mark.api
class TestRatingsCrud:

    @allure.title("Создать отзыв на tincan-курс (через материал БЗ) -> получить -> my-review -> удалить")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_full_review_cycle_on_tincan_course(
        self, api_client, ratings_endpoint, created_course, created_rating
    ):
        with allure.step("Обернуть tincan-курс материалом БЗ (created_course)"):
            material = created_course()
            entity_id = material["id"]

        with allure.step("Создать отзыв POST /ratings"):
            rating_data = created_rating(
                rating=5, entity_type=ENTITY_TYPE_KB_MATERIAL, entity_id=entity_id, body="Отличный курс"
            )
            rating_id = rating_data["id"]
            assert rating_data["rating"] == 5
            assert rating_data["body"] == "Отличный курс"
            assert rating_data["entity_type"] == ENTITY_TYPE_KB_MATERIAL
            assert rating_data["entity_id"] == entity_id

        with allure.step("Получить отзыв по id GET /ratings/{id}"):
            fetched = ratings_endpoint.get_rating(rating_id)
            assert fetched["id"] == rating_id
            assert fetched["body"] == "Отличный курс"

        with allure.step("GET /ratings/my-review — тот же отзыв"):
            my_review = ratings_endpoint.get_my_review(ENTITY_TYPE_KB_MATERIAL, entity_id)
            assert my_review["id"] == rating_id

        with allure.step("Отзыв виден в общем списке GET /ratings"):
            all_ratings = ratings_endpoint.list_ratings()
            assert any(r["id"] == rating_id for r in all_ratings)

        with allure.step("DELETE /ratings/my-review удаляет отзыв"):
            assert ratings_endpoint.delete_my_review(ENTITY_TYPE_KB_MATERIAL, entity_id) is True

        with allure.step("После удаления GET /ratings/my-review → 200 с пустыми данными"):
            resp = api_client.get(f"/ratings/my-review?entity_type={ENTITY_TYPE_KB_MATERIAL}&entity_id={entity_id}")
            assert resp.status_code == 200
            assert not resp.json().get("data")

    @allure.title("Обычный слушатель может создать отзыв на материал БЗ, не будучи назначенным на курс")
    def test_listener_can_review_without_assignment(
        self, created_course, second_user_ratings_endpoint, created_rating
    ):
        material = created_course()
        entity_id = material["id"]

        _user, listener_ratings = second_user_ratings_endpoint()
        rating_data = created_rating(
            endpoint=listener_ratings,
            rating=4,
            entity_type=ENTITY_TYPE_KB_MATERIAL,
            entity_id=entity_id,
            body="Отзыв слушателя",
        )
        assert rating_data["rating"] == 4
        assert rating_data["entity_id"] == entity_id

    @allure.title("Сырой tincan (entity_type=activity) — известное ограничение: всегда 'Not reviewable entity'")
    def test_raw_tincan_activity_is_not_reviewable(
        self, api_client, created_tincan, assigned_user, tincan_endpoint
    ):
        """Эмпирическая проверка гипотезы из плана задачи (created_program/created_stream/
        created_tincan/assigned_user): даже когда активность реально назначена слушателю,
        entity_type="activity" с id самого tincan отвечает 422 "Not reviewable entity" —
        и для админа, и для назначенного слушателя. Рабочий путь — entity_type=
        "knowledge_base_material" через материал БЗ (см. test_full_review_cycle_on_tincan_course),
        не сырая активность."""
        tincan = created_tincan()
        bundle = assigned_user()
        assigned = tincan_endpoint.assign_activities([tincan["id"]], [bundle["user"]["id"]])
        assert assigned

        resp = api_client.post(
            "/ratings",
            json={"data": {"attributes": {"rating": 5, "entity_type": "activity", "entity_id": tincan["id"]}}},
        )
        assert resp.status_code == 422
        assert "Not reviewable entity" in resp.text
