from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class HomeworkPassFailEndpoint:
    """Методы для работы с практическими заданиями (зачёт/незачёт)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание практического задания. Возвращает данные созданного задания."""
        # Принудительно выставляем зачёт/незачёт
        payload["data"]["attributes"]["grade_type"] = "pass_fail"
        resp = self.client.post("/content", json=payload)
        assert resp.status_code in (200, 201), (
            f"Homework (pass_fail) create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"Homework (pass_fail) created: ID={data['id']}, name={data['attributes'].get('name')}")
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
            logger.info(f"Homeworks (pass_fail) deleted: {content_ids}")
        else:
            logger.warning(f"Homeworks (pass_fail) delete failed: {resp.status_code}")
        return success