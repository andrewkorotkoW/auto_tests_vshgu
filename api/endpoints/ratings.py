from typing import Dict, List
from urllib.parse import urlencode

from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class RatingsEndpoint:
    """Методы для работы с рейтингами/отзывами (docs/qr_code_ratings_recon.md,
    раздел «Рейтинги/отзывы»)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def list_ratings(self, **filters) -> List[Dict]:
        """GET /ratings(?filters) → 200, пагинированный список всех отзывов всех сущностей
        (не только своих), элемент — плоская структура с id/body/status/rating/entity_type/
        entity_id/author/reviewer (без фильтров подтверждено разведкой; конкретные ключи
        фильтров разведкой не проверялись, передаются как есть)."""
        query = f"?{urlencode(filters)}" if filters else ""
        resp = self.client.get(f"/ratings{query}")
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def create_rating(self, rating, entity_type: str, entity_id: int, **extra) -> Dict:
        """POST /ratings, конверт {"data": {"attributes": {"rating", "entity_type",
        "entity_id", **extra}}} — обязательность этих трёх полей подтверждена разведкой по
        422 (путь ошибки указывает ровно на этот конверт); реальный успешный ответ разведкой
        не проверен."""
        payload = {
            "data": {
                "attributes": {
                    "rating": rating,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    **extra,
                }
            }
        }
        resp = self.client.post("/ratings", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Rating created: entity_type={entity_type}, entity_id={entity_id}")
        return data

    def get_rating(self, rating_id: int) -> Dict:
        """GET /ratings/{rating} — маршрут не вызывался живым запросом в разведке."""
        resp = self.client.get(f"/ratings/{rating_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def get_my_review(self, entity_type: str, entity_id: int) -> Dict:
        """GET /ratings/my-review?entity_type=&entity_id= — «мой отзыв конкретно на эту
        сущность», оба параметра обязательны (422 без них, подтверждено разведкой)."""
        query = urlencode({"entity_type": entity_type, "entity_id": entity_id})
        resp = self.client.get(f"/ratings/my-review?{query}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete_my_review(self, entity_type: str, entity_id: int) -> bool:
        """DELETE /ratings/my-review?entity_type=&entity_id= — оба параметра обязательны
        (422 без них, подтверждено разведкой)."""
        query = urlencode({"entity_type": entity_type, "entity_id": entity_id})
        resp = self.client.delete(f"/ratings/my-review?{query}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"My review deleted: entity_type={entity_type}, entity_id={entity_id}")
        else:
            logger.warning(f"Delete my review failed: {resp.status_code} {resp.text[:200]}")
        return success

    def change_rating_status(self, review_ids: list, status) -> Dict:
        """POST /ratings/change-status, конверт {"data": {"attributes": {"review_ids",
        "status"}}} — bulk-операция над списком id отзывов, доступна только admin (403
        обычному пользователю), подтверждено разведкой. Допустимые значения status разведкой
        не выяснены."""
        payload = {
            "data": {
                "attributes": {
                    "review_ids": review_ids,
                    "status": status,
                }
            }
        }
        resp = self.client.post("/ratings/change-status", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()
        logger.info(f"Rating status changed: review_ids={review_ids}, status={status}")
        return data

    def export_ratings(self, **filters) -> Dict:
        """POST /ratings/export → 200 {"result": "ok"} — синхронный, без обязательных полей,
        подтверждено разведкой (пустое тело {} уже проходит для admin и для обычного
        пользователя)."""
        resp = self.client.post("/ratings/export", json=filters)
        expect_status(resp, 200)
        data = resp.json()
        logger.info("Ratings export requested")
        return data
