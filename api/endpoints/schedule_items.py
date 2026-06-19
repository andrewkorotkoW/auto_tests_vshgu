from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class ScheduleItemsEndpoint:
    """Методы для работы с элементами расписания."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, program_id: int, stream_id: int, module_id: int, payload: dict) -> Dict:
        """Создание элемента расписания в модуле."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items",
            json=payload
        )
        assert resp.status_code in (200, 201), (
            f"Schedule item create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"Schedule item created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int, stream_id: int, module_id: int, item_id: int) -> Dict:
        """Получение элемента расписания по ID."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}"
        )
        assert resp.status_code == 200, f"Get schedule item failed: {resp.status_code}"
        return resp.json()["data"]

    def delete(self, program_id: int, stream_id: int, module_id: int, item_id: int) -> bool:
        """Удаление элемента расписания."""
        resp = self.client.delete(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}"
        )
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Schedule item deleted: ID={item_id}")
        else:
            logger.warning(f"Schedule item delete failed: ID={item_id}, status={resp.status_code}")
        return success