from typing import Dict
from api.client import ApiClient
from utils.logger import logger
from api.helpers.expectations import expect_status


class StreamsEndpoint:
    """Методы для работы с потоками."""

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, program_id: int, payload: dict) -> Dict:
        """Создание потока для программы."""
        resp = self.client.post(f"/programs/{program_id}/streams", json=payload)
        expect_status(resp, (200, 201))
        data = resp.json()["data"]
        logger.info(f"Stream created: ID={data['id']}, name={data['attributes'].get('name')}")
        return data

    def get(self, program_id: int, stream_id: int) -> Dict:
        """Получение потока по ID."""
        resp = self.client.get(f"/programs/{program_id}/streams/{stream_id}")
        expect_status(resp, 200)
        return resp.json()["data"]

    def delete(self, program_id: int, stream_id: int) -> bool:
        """Удаление потока."""
        resp = self.client.delete(f"/programs/{program_id}/streams/{stream_id}")
        success = resp.status_code in (200, 204)
        if success:
            logger.info(f"Stream deleted: ID={stream_id}")
        else:
            logger.warning(f"Stream delete failed: ID={stream_id}, status={resp.status_code}")
        return success