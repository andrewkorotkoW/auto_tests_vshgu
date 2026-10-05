from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class HomeworkTenPointEndpoint:
    """Методы для работы с практическими заданиями (10‑балльная система)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание практического задания. Возвращает данные созданного задания."""
        # Принудительно выставляем десятибалльную шкалу
        payload["data"]["attributes"]["grade_type"] = "ten_point"
        resp = self.client.post("/content", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Homework (ten_point) created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def delete(self, content_id: int) -> bool:
        """Удаление одного задания."""
        return self.mass_delete([content_id])

    def mass_delete(self, content_ids: list) -> bool:
        """Массовое удаление заданий."""
        payload = {
            "data": {
                "attributes": {
                    "content_ids": content_ids
                }
            }
        }
        resp = self.client.delete("/activities/mass-delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Homeworks (ten_point) deleted: {content_ids}")
        else:
            logger.warning(f"Homeworks (ten_point) delete failed: {resp.status_code}")
        return success