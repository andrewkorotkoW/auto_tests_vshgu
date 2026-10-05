from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


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
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Module created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int, stream_id: int, module_id: int) -> Dict:
        """Получение модуля по ID."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}"
        )
        expect_status(resp, 200)
        return resp.json()["data"]

    def update(self, program_id: int, stream_id: int, module_id: int, payload: dict) -> Dict:
        """Обновление модуля (PUT)."""
        resp = self.client.put(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}",
            json=payload
        )
        expect_status(resp, 200)
        data = resp.json()["data"]
        logger.info(f"Module updated: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get_contents(self, program_id: int, stream_id: int, module_id: int) -> list:
        """Контент модуля (обёртки stream_content вокруг content_id активити/курсов) —
        нужен, чтобы найти stream_content_id по content_id для смены статуса прохождения."""
        resp = self.client.get(
            f"/programs/{program_id}/streams/{stream_id}/modules/{module_id}/contents"
        )
        expect_status(resp, 200)
        return resp.json().get("data", [])

    def find_stream_content_id(self, program_id: int, stream_id: int, module_id: int, content_id: int) -> int:
        """Найти stream_content_id (id обёртки) по content_id активити/курса в модуле."""
        for item in self.get_contents(program_id, stream_id, module_id):
            content = item.get("attributes", {}).get("content", {})
            if int(content.get("id", 0)) == content_id:
                return int(item["id"])
        raise AssertionError(
            f"В модуле id={module_id} не найден content_id={content_id}"
        )

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