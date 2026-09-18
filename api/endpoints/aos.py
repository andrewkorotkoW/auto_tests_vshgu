from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class AosEndpoint:
    """Методы для работы с АОС (тесты)."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict) -> Dict:
        """Создание АОС."""
        resp = self.client.post("/tests", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"AOS created: ID={data.get('content_id')}, name={data.get('name')}")
        return data

    def get(self, aos_id: int) -> Dict:
        """Получение АОС по ID."""
        resp = self.client.get(f"/tests/{aos_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def activate(self, program_id: int, stream_id: int, aos_id: int) -> bool:
        """Активация/деактивация АОС."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/feedback/{aos_id}/change-active",
            json={}
        )
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"AOS activated: ID={aos_id}")
        else:
            logger.warning(f"AOS activate failed: ID={aos_id}, status={resp.status_code}")
        return success

    def mass_delete(self, content_ids: list) -> bool:
        payload = {"data": {"attributes": {"content_ids": content_ids}}}
        resp = self.client.delete("/activities/mass-delete", json=payload)
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"AOS mass deleted: {content_ids}")
        else:
            logger.warning(f"AOS mass delete failed: {resp.status_code}")
        return success
