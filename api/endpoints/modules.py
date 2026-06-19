from typing import Dict
from api.client import ApiClient
from utils.logger import logger


class ModulesEndpoint:
    """Методы для работы с модулями."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, program_id: int, stream_id: int, payload: dict) -> Dict:
        """Создание модуля в потоке."""
        resp = self.client.post(
            f"/programs/{program_id}/streams/{stream_id}/modules",
            json=payload
        )
        assert resp.status_code in (200, 201), (
            f"Module create failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"Module created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int, stream_id: int, module_id: int) -> Dict:
        """Получение модуля по ID."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
        )
        assert resp.status_code == 200, f"Get module failed: {resp.status_code}"
        return resp.json()["data"]

    def update(self, program_id: int, stream_id: int, module_id: int, payload: dict) -> Dict:
        """Обновление модуля (PUT)."""
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}",
            json=payload
        )
        assert resp.status_code == 200, (
            f"Module update failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()["data"]
        logger.info(f"Module updated: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def delete(self, program_id: int, stream_id: int, module_id: int) -> bool:
        """Удаление модуля."""
        resp = self.client.delete(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
        )
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Module deleted: ID={module_id}")
        else:
            logger.warning(f"Module delete failed: ID={module_id}, status={resp.status_code}")
        return success