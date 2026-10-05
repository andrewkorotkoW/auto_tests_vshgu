from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


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
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Schedule item created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int, stream_id: int, module_id: int, item_id: int) -> Dict:
        """Получение элемента расписания по ID."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/schedule-items/{item_id}"
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def register_user(self, item_id: int, user_id: int, is_registered: bool = True) -> Dict:
        """Отметить регистрацию пользователя на очное мероприятие — влияет на
        completeness_schedule_items в статистике дашборда программ."""
        resp = self.client.post(
            f"/schedule-item/{item_id}/user/{user_id}/update-registration-status",
            json={"data": {"attributes": {"is_registered": is_registered}}}
        )
        expect_status(resp, (200, 201))
        logger.info(f"Schedule item registration: item={item_id}, user={user_id}, is_registered={is_registered}")
        return resp.json()

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